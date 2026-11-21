from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QProgressBar, QProgressDialog, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from core import simple
from core.ffpath import app_dir, find_tool
from core.i18n import tr
from core.installer import InstallWorker
from core.probe import MediaInfo, probe
from core.runner import Job, JobRunner
from core.thumb import Thumbs
from ui import icons
from ui.format_grid import FormatGrid
from ui.preview import PreviewCard
from ui.settings_dialog import SettingsDialog, load as load_settings

PAGE_DROP, PAGE_PICK, PAGE_RUN = 0, 1, 2


class MainWindow(QMainWindow):
    """화면 3개: 1) 파일 넣기 -> 2) 형식 고르기 -> 3) 변환 진행."""

    @staticmethod
    def _drop_guide_text() -> str:
        return tr("여기에 파일을 끌어다 놓거나 눌러서 선택하세요")

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Swapeg")
        self.resize(820, 600)
        self.setMinimumSize(560, 460)
        self.setAcceptDrops(True)

        self.settings = QSettings("Swapeg", "Swapeg")
        custom = self.settings.value("ffmpeg_dir", None)  # 설정에서 직접 지정한 ffmpeg 폴더
        self.ffmpeg = find_tool("ffmpeg", custom)
        self.ffprobe = find_tool("ffprobe", custom)
        self.items: list[dict] = []        # {path, info, kind}
        self._job_files: list[dict] = []
        self._results: list[tuple[str, bool, str]] = []   # (파일명, 성공, 메시지)
        self._last_err = ""
        self._last_dir = ""
        self._cancelled = False

        self.thumbs = Thumbs(lambda: self.ffmpeg, self)
        self.runner = JobRunner(self)
        self.runner.job_started.connect(self._on_job_started)
        self.runner.progress.connect(self._on_progress)
        self.runner.log.connect(self._remember_log)
        self.runner.job_finished.connect(self._on_job_finished)
        self.runner.all_finished.connect(self._on_all_finished)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_drop_page())
        self.stack.addWidget(self._build_pick_page())
        self.stack.addWidget(self._build_run_page())

        if not self.ffmpeg or not self.ffprobe:
            QTimer.singleShot(300, self._offer_install)

    # ================================================================ 화면 만들기
    def _page(self) -> tuple[QWidget, QVBoxLayout]:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(14)
        return w, v

    def _build_drop_page(self) -> QWidget:
        # 제목은 왼쪽 위(드롭 구역 밖), 그 아래 나머지 창 전체가 드롭 구역. 구역 안에는 안내문만 둔다.
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(28, 22, 28, 22)
        outer.setSpacing(14)
        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(app_dir() / "assets" / "icon.png")).scaled(
            34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        title = QLabel("Swapeg")
        title.setObjectName("Title")
        head.addWidget(logo)
        head.addWidget(title)
        head.addStretch(1)
        head.addWidget(self._gear_button())
        outer.addLayout(head)
        self.drop = QPushButton()
        self.drop.setObjectName("DropZone")
        self.drop.setCursor(Qt.PointingHandCursor)
        self.drop.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 창 전체를 덮는다
        self.drop.clicked.connect(self._add_dialog)
        inner = QVBoxLayout(self.drop)
        inner.addStretch(1)
        art = QLabel()
        art.setPixmap(icons.pixmap("upload", icons.GREEN, 84, 1.6))
        self.drop_guide = QLabel(self._drop_guide_text())
        self.drop_guide.setObjectName("DropGuide")
        # 지원하는 종류를 아이콘으로 안내
        kinds = QHBoxLayout()
        kinds.addStretch(1)
        for kind in ("video", "audio", "image"):
            ic = QLabel()
            ic.setPixmap(icons.pixmap(kind, icons.MUTED, 20, 1.8))
            tx = QLabel(tr(simple.KIND_TITLE[kind]))
            tx.setObjectName("DropHint")
            kinds.addWidget(ic)
            kinds.addWidget(tx)
            kinds.addSpacing(14)
        more = QLabel(tr("{n}개 형식 지원 · 원본 화질 유지", n=len(simple.TARGET_KIND)))
        more.setObjectName("DropHint")
        kinds.addWidget(more)
        kinds.addStretch(1)
        for lab in (art, self.drop_guide):
            lab.setAlignment(Qt.AlignCenter)
        inner.addWidget(art)
        inner.addWidget(self.drop_guide)
        inner.addSpacing(10)
        inner.addLayout(kinds)
        inner.addStretch(1)
        # 클릭은 구역 전체가 받도록 안쪽 위젯은 마우스 이벤트를 통과시킨다
        for child in self.drop.findChildren(QLabel):
            child.setAttribute(Qt.WA_TransparentForMouseEvents)
        outer.addWidget(self.drop, 1)
        return w

    def _gear_button(self) -> QPushButton:
        b = QPushButton(tr("설정"))
        b.setProperty("ghost", True)
        b.setIcon(icons.icon("gear"))
        b.setIconSize(QSize(18, 18))
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(self._open_settings)
        return b

    def _build_pick_page(self) -> QWidget:
        w, v = self._page()
        top = QHBoxLayout()
        back = QPushButton(tr("처음으로"))
        back.setProperty("ghost", True)
        back.setIcon(icons.icon("back"))
        back.setIconSize(QSize(18, 18))
        back.clicked.connect(self._reset)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("검색  (예: mp3, 영상, 이미지)"))
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(260)
        self.search.addAction(icons.icon("search", icons.MUTED), QLineEdit.LeadingPosition)
        top.addWidget(back)
        top.addStretch(1)
        top.addWidget(self.search)
        top.addWidget(self._gear_button())
        v.addLayout(top)

        self.grid = FormatGrid()
        self.grid.set_preferred(self.settings.value("last_format", None))
        self.grid.changed.connect(self._on_format_changed)
        self.search.textChanged.connect(self.grid.filter)
        self.search.returnPressed.connect(self._search_enter)

        # 왼쪽: 넣은 파일 미리보기, 오른쪽: 형식 상자들
        body = QHBoxLayout()
        body.setSpacing(18)
        self.pick_card = PreviewCard(self.thumbs, (200, 130))
        left = QVBoxLayout()
        left.addWidget(self.pick_card)
        left.addStretch(1)
        body.addLayout(left)
        body.addWidget(self.grid, 1)
        v.addLayout(body, 1)

        bottom = QHBoxLayout()
        b_more = QPushButton(tr("파일 추가"))
        b_more.setIcon(icons.icon("plus"))
        b_more.clicked.connect(self._add_dialog)
        self.btn_go = QPushButton(tr("변환"))
        self.btn_go.setIcon(icons.icon("swap", icons.MINT_DARK))
        self.btn_go.setIconSize(QSize(20, 20))
        self.btn_go.setProperty("primary", True)
        self.btn_go.setMinimumWidth(150)
        self.btn_go.clicked.connect(self._start)
        bottom.addWidget(b_more)
        bottom.addStretch()
        bottom.addWidget(self.btn_go)
        v.addLayout(bottom)
        return w

    def _build_run_page(self) -> QWidget:
        w, v = self._page()
        v.addStretch(1)
        self.run_cap = QLabel("")
        self.run_cap.setObjectName("SectionLabel")
        self.run_cap.setAlignment(Qt.AlignCenter)
        self.run_card = PreviewCard(self.thumbs, (260, 150), show_sub=False)
        v.addWidget(self.run_cap)
        v.addWidget(self.run_card, 0, Qt.AlignHCenter)
        self.run_title = QLabel(tr("변환 중..."))
        self.run_title.setObjectName("BigTitle")
        self.run_title.setAlignment(Qt.AlignCenter)
        self.run_pct = QLabel("0%")
        self.run_pct.setObjectName("BigPct")
        self.run_pct.setAlignment(Qt.AlignCenter)
        self.run_bar = QProgressBar()
        self.run_bar.setObjectName("BigBar")
        self.run_bar.setRange(0, 1000)
        self.run_bar.setTextVisible(False)
        self.run_file = QLabel("")
        self.run_file.setObjectName("Muted")
        self.run_file.setAlignment(Qt.AlignCenter)
        self.run_detail = QLabel("")
        self.run_detail.setObjectName("Error")
        self.run_detail.setWordWrap(True)
        self.run_detail.setAlignment(Qt.AlignCenter)
        for wd in (self.run_title, self.run_pct):
            v.addWidget(wd)
        bar_row = QHBoxLayout()
        bar_row.addStretch(1)
        bar_row.addWidget(self.run_bar, 6)
        bar_row.addStretch(1)
        v.addLayout(bar_row)
        v.addWidget(self.run_file)
        v.addWidget(self.run_detail)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_cancel = QPushButton(tr("취소"))
        self.btn_cancel.setIcon(icons.icon("close", icons.MUTED))
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_open = QPushButton(tr("폴더 열기"))
        self.btn_open.setIcon(icons.icon("folder"))
        self.btn_again = QPushButton(tr("새로 변환하기"))
        self.btn_again.setIcon(icons.icon("swap", icons.MINT_DARK))
        self.btn_again.setProperty("primary", True)
        self.btn_open.clicked.connect(self._open_folder)
        self.btn_again.clicked.connect(self._reset)
        for b in (self.btn_cancel, self.btn_open, self.btn_again):
            btns.addWidget(b)
        btns.addStretch(1)
        v.addLayout(btns)
        v.addStretch(2)
        return w

    # ================================================================ 파일 넣기
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and self.stack.currentIndex() != PAGE_RUN:
            e.acceptProposedAction()

    def dropEvent(self, e):
        self._add_files([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def _add_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, tr("파일 선택"), self._last_dir, tr("모든 파일 (*.*)"))
        self._add_files(paths)

    def _add_files(self, paths: list[str]) -> None:
        if self.runner.running or self.stack.currentIndex() == PAGE_RUN:
            return
        unreadable = []
        added = 0
        for p in paths:
            if not Path(p).is_file() or any(it["path"] == p for it in self.items):
                continue
            info = probe(self.ffprobe, p) if self.ffprobe else MediaInfo()
            if self.ffprobe and info.vcodec is None and info.acodec is None:
                unreadable.append(Path(p).name)  # ffmpeg가 읽을 수 없는 파일
                continue
            self.items.append({"path": p, "info": info, "kind": simple.kind_of(p, info)})
            self._last_dir = str(Path(p).parent)
            added += 1
        self.drop_guide.setText(tr("읽을 수 없는 파일: {names}", names=", ".join(unreadable)) if unreadable
                                else self._drop_guide_text())
        if self.items and (added or self.stack.currentIndex() == PAGE_PICK):
            self._enter_pick()

    # ================================================================ 형식 고르기
    def _enter_pick(self) -> None:
        n = len(self.items)
        first = self.items[0]
        name = Path(first["path"]).name
        sub = first["info"].summary()
        self.pick_card.show_file(first["path"], name if n == 1 else tr("{name} 외 {n}개", name=name, n=n - 1),
                                 sub, self._seek_hint(first))
        self.search.clear()
        # 원본과 같은 확장자는 목록에서 뺀다 (mp4 파일에 MP4로 바꾸기 같은 건 의미가 없으므로)
        self.grid.rebuild(lambda ext, tk: any(
            simple.can_convert(it["kind"], simple.ext_of(it["path"]), ext, tk) for it in self.items))
        self.stack.setCurrentIndex(PAGE_PICK)

    @staticmethod
    def _seek_hint(item: dict) -> float:
        """영상은 처음 검은 화면을 피하려고 20% 지점의 프레임을 쓴다."""
        d = item["info"].duration
        return min(d * 0.2, 10.0) if item["kind"] == "video" and d else 0.0

    def _on_format_changed(self, ext: str) -> None:
        if ext:
            self.settings.setValue("last_format", ext)
        self.btn_go.setEnabled(bool(ext))
        self.btn_go.setText(tr("{fmt}(으)로 변환", fmt=simple.label_of(ext)) if ext else tr("변환"))

    def _search_enter(self) -> None:
        ext = self.grid.first_visible()
        if ext:
            self.grid.select(ext)

    def _reset(self) -> None:
        if self.runner.running:
            return
        self.items.clear()
        self.drop_guide.setText(self._drop_guide_text())
        self.stack.setCurrentIndex(PAGE_DROP)

    # ================================================================ 변환
    def _start(self) -> None:
        if not self.ffmpeg:
            self._offer_install()
            return
        target = self.grid.current()
        if not target or not self.items:
            return
        cfg = load_settings(self.settings)
        out_dir = cfg["out_dir"] if cfg["out_mode"] == "custom" and cfg["out_dir"] else None
        if out_dir:
            try:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
            except OSError as e:
                QMessageBox.warning(self, tr("저장 위치"), tr("저장 폴더를 만들 수 없습니다.\n{err}", err=e))
                return
        jobs, self._job_files, self._results, self._outs = [], [], [], []
        self._ok_outs: list[str] = []
        for it in self.items:
            src = it["path"]
            name = Path(src).name
            if simple.ext_of(src) == target:
                self._results.append((name, False, tr("이미 같은 형식이에요")))
                continue
            if not simple.can_convert(it["kind"], simple.ext_of(src), target):
                self._results.append((name, False, tr("이 형식으로는 바꿀 수 없어요")))
                continue
            out = simple.output_path(src, target, out_dir)
            args = simple.build_args(self.ffmpeg, src, str(out), target, it["info"], it["kind"],
                                     cfg["quality"])
            jobs.append(Job(args, str(out), it["info"].duration))
            self._job_files.append(it)
            self._outs.append(str(out))
        if not jobs:
            QMessageBox.information(self, tr("알림"), tr("선택한 형식으로 바꿀 수 있는 파일이 없습니다."))
            return
        self._cancelled = False
        self.run_title.setText(tr("변환 중..."))
        self.run_pct.setText("0%")
        self.run_bar.setValue(0)
        self.run_file.setText("")
        self.run_detail.setText("")
        self.run_cap.setText(tr("변환 중인 파일"))
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_open.hide()
        self.btn_again.hide()
        self.stack.setCurrentIndex(PAGE_RUN)
        self.runner.start(jobs)

    def _cancel(self) -> None:
        self._cancelled = True
        self.btn_cancel.setEnabled(False)
        self.run_title.setText(tr("취소하는 중..."))
        self.runner.cancel()

    def _on_job_started(self, i: int) -> None:
        self._last_err = ""
        name = Path(self._job_files[i]["path"]).name
        total = len(self._job_files)
        self.run_file.setText(f"{name}  ({i + 1}/{total})")
        it = self._job_files[i]
        self.run_card.show_file(it["path"], name, "", self._seek_hint(it))

    def _on_progress(self, i: int, frac: float) -> None:
        overall = (i + frac) / len(self._job_files)
        self.run_bar.setValue(int(overall * 1000))
        self.run_pct.setText(f"{overall * 100:.0f}%")

    def _remember_log(self, text: str) -> None:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            self._last_err = lines[-1]

    def _on_job_finished(self, i: int, ok: bool, msg: str) -> None:
        name = Path(self._job_files[i]["path"]).name
        detail = msg
        if not ok and not self._cancelled and self._last_err:
            detail = f"{msg}: {self._last_err[:80]}"   # ffmpeg가 남긴 마지막 오류 줄
        self._results.append((name, ok, detail))
        if ok:
            self._ok_outs.append(self._outs[i])

    def _on_all_finished(self) -> None:
        done = sum(1 for _n, ok, _m in self._results if ok)
        bad = [(n, m) for n, ok, m in self._results if not ok]
        self.btn_cancel.hide()
        self.btn_again.show()
        if done:
            self.btn_open.show()
        if self._cancelled:
            self.run_title.setText(tr("취소되었습니다"))
        elif bad and not done:
            self.run_title.setText(tr("변환에 실패했어요"))
        else:
            self.run_title.setText(tr("완료!"))
            self.run_bar.setValue(1000)
            self.run_pct.setText("100%")
        self.run_file.setText(tr("{n}개 변환 완료", n=done) + (tr(" · {n}개 실패/건너뜀", n=len(bad)) if bad else ""))
        self.run_detail.setText("\n".join(f"{n}: {m}" for n, m in bad[:5]))
        if self._ok_outs:  # 변환된 결과 미리보기 (여러 개면 첫 번째)
            out = self._ok_outs[0]
            dur = self._job_files[self._outs.index(out)]["info"].duration
            label = Path(out).name if len(self._ok_outs) == 1 else tr(
                "{name} 외 {n}개", name=Path(out).name, n=len(self._ok_outs) - 1)
            self.run_cap.setText(tr("결과 미리보기"))
            self.run_card.show_file(out, label, "", min(dur * 0.2, 10.0) if dur else 0.0)
            self._last_dir = str(Path(out).parent)   # [폴더 열기]는 결과가 저장된 폴더를 연다
            if load_settings(self.settings)["open_after"] and not self._cancelled:
                self._open_folder()
        else:
            self.run_cap.setText("")

    def _open_folder(self) -> None:
        if self._last_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_dir))

    # ================================================================ 설정
    def _open_settings(self) -> None:
        if self.runner.running:
            return
        SettingsDialog(self.settings, self.ffmpeg, self._pick_ffmpeg,
                       lambda: self._offer_install(force=True), self._ask_restart, self).exec()

    def _ask_restart(self) -> None:
        """언어는 화면을 다시 만들어야 해서 앱을 다시 시작해야 적용된다."""
        ans = QMessageBox.question(self, "Swapeg", tr("언어를 바꾸려면 Swapeg를 다시 시작해야 합니다.\n지금 다시 시작할까요?"))
        if ans != QMessageBox.Yes:
            return
        args = sys.argv[1:] if getattr(sys, "frozen", False) else sys.argv
        QProcess.startDetached(sys.executable, args)
        QApplication.quit()

    def _pick_ffmpeg(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("ffmpeg.exe / ffprobe.exe 가 있는 폴더 선택"))
        if not d:
            return
        ff, fp = find_tool("ffmpeg", d), find_tool("ffprobe", d)
        if ff and fp and Path(ff).parent == Path(d) == Path(fp).parent:
            self.settings.setValue("ffmpeg_dir", d)
            self.ffmpeg, self.ffprobe = ff, fp
            QMessageBox.information(self, "ffmpeg", tr("ffmpeg 경로를 설정했습니다.\n{path}", path=ff))
        else:
            QMessageBox.warning(self, "ffmpeg", tr("선택한 폴더에 ffmpeg.exe와 ffprobe.exe가 함께 있어야 합니다."))

    # ================================================================ ffmpeg 설치
    def _offer_install(self, force: bool = False) -> None:
        if self.ffmpeg and self.ffprobe and not force:
            return
        ans = QMessageBox.question(
            self, tr("ffmpeg 설치"),
            (tr("ffmpeg를 다시 설치합니다. ") if force else tr("ffmpeg가 없습니다. "))
            + tr("지금 자동으로 내려받아 앱 폴더의 bin 에 설치할까요?\n\n출처: gyan.dev 릴리스 빌드 (약 100MB, GPL 라이선스)\n"
                 "다운로드 후 SHA-256 체크섬을 검증합니다."))
        if ans != QMessageBox.Yes:
            return
        self._dlg = QProgressDialog(tr("준비 중..."), tr("취소"), 0, 100, self)
        self._dlg.setWindowTitle(tr("ffmpeg 설치"))
        self._dlg.setWindowModality(Qt.WindowModal)
        self._dlg.setMinimumDuration(0)
        self._dlg.setAutoClose(False)
        self._dlg.setAutoReset(False)
        w = InstallWorker(app_dir() / "bin", parent=self)
        self._installer = w
        w.status.connect(self._dlg.setLabelText)
        w.progress.connect(self._on_install_progress)
        w.finished_ok.connect(self._on_install_ok)
        w.failed.connect(self._on_install_failed)
        self._dlg.canceled.connect(w.cancel)
        w.start()

    def _on_install_progress(self, done: int, total: int) -> None:
        if total:
            self._dlg.setValue(int(done * 100 / total))
            self._dlg.setLabelText(tr("ffmpeg 다운로드 중... {done:.0f} / {total:.0f} MB",
                                      done=done / 1e6, total=total / 1e6))
        else:
            self._dlg.setRange(0, 0)

    def _on_install_ok(self, _folder: str) -> None:
        self._dlg.close()
        self.settings.remove("ffmpeg_dir")   # 앱 폴더에 새로 설치했으니 직접 지정한 경로는 해제
        self.ffmpeg, self.ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
        QMessageBox.information(self, "ffmpeg", tr("설치가 완료되었습니다."))

    def _on_install_failed(self, msg: str) -> None:
        self._dlg.close()
        QMessageBox.warning(self, tr("ffmpeg 설치 실패"), msg)
