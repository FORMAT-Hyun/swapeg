from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QProgressDialog, QPushButton, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget,
)

from core import simple
from core.ffpath import app_dir, find_tool
from core.installer import InstallWorker
from core.probe import MediaInfo, probe
from core.runner import Job, JobRunner
from ui.format_grid import FormatGrid

PAGE_DROP, PAGE_PICK, PAGE_RUN = 0, 1, 2


class MainWindow(QMainWindow):
    """화면 3개: 1) 파일 넣기 -> 2) 형식 고르기 -> 3) 변환 진행."""

    DROP_GUIDE = "여기에 파일을 끌어다 놓거나 눌러서 선택하세요"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg 변환기")
        self.resize(820, 600)
        self.setMinimumSize(560, 460)
        self.setAcceptDrops(True)

        self.settings = QSettings("FFmpegGUI", "converter")
        self.ffmpeg = find_tool("ffmpeg")
        self.ffprobe = find_tool("ffprobe")
        self.items: list[dict] = []        # {path, info, kind}
        self._job_files: list[dict] = []
        self._results: list[tuple[str, bool, str]] = []   # (파일명, 성공, 메시지)
        self._last_err = ""
        self._last_dir = ""
        self._cancelled = False

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
        title = QLabel("FFmpeg 변환기")
        title.setObjectName("Title")
        outer.addWidget(title)
        self.drop = QPushButton()
        self.drop.setObjectName("DropZone")
        self.drop.setCursor(Qt.PointingHandCursor)
        self.drop.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 창 전체를 덮는다
        self.drop.clicked.connect(self._add_dialog)
        inner = QVBoxLayout(self.drop)
        self.drop_guide = QLabel(self.DROP_GUIDE)
        self.drop_guide.setObjectName("DropGuide")
        self.drop_guide.setAlignment(Qt.AlignCenter)
        self.drop_guide.setAttribute(Qt.WA_TransparentForMouseEvents)  # 클릭은 구역 전체가 받는다
        inner.addWidget(self.drop_guide)
        outer.addWidget(self.drop, 1)
        return w

    def _build_pick_page(self) -> QWidget:
        w, v = self._page()
        top = QHBoxLayout()
        back = QPushButton("← 처음으로")
        back.setProperty("ghost", True)
        back.clicked.connect(self._reset)
        self.file_label = QLabel("")
        self.file_label.setObjectName("Muted")
        self.search = QLineEdit()
        self.search.setPlaceholderText("검색  (예: mp3, 영상, 이미지)")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(240)
        top.addWidget(back)
        top.addWidget(self.file_label, 1)
        top.addWidget(self.search)
        v.addLayout(top)

        self.grid = FormatGrid()
        self.grid.set_preferred(self.settings.value("last_format", None))
        self.grid.changed.connect(self._on_format_changed)
        self.search.textChanged.connect(self.grid.filter)
        self.search.returnPressed.connect(self._search_enter)
        v.addWidget(self.grid, 1)

        bottom = QHBoxLayout()
        b_more = QPushButton("파일 추가")
        b_more.clicked.connect(self._add_dialog)
        self.btn_go = QPushButton("변환")
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
        self.run_title = QLabel("변환 중...")
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
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.clicked.connect(self._cancel)
        self.btn_open = QPushButton("폴더 열기")
        self.btn_again = QPushButton("새로 변환하기")
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
        paths, _ = QFileDialog.getOpenFileNames(self, "파일 선택", self._last_dir, "모든 파일 (*.*)")
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
        self.drop_guide.setText(("읽을 수 없는 파일: " + ", ".join(unreadable)) if unreadable
                                else self.DROP_GUIDE)
        if self.items and (added or self.stack.currentIndex() == PAGE_PICK):
            self._enter_pick()

    # ================================================================ 형식 고르기
    def _enter_pick(self) -> None:
        n = len(self.items)
        first = self.items[0]
        name = Path(first["path"]).name
        self.file_label.setText(
            f"{name}  ·  {first['info'].summary()}" if n == 1 else f"{name} 외 {n - 1}개")
        self.search.clear()
        self.grid.rebuild(lambda ext: any(
            simple.can_convert(it["kind"], simple.ext_of(it["path"]), ext) for it in self.items))
        self.stack.setCurrentIndex(PAGE_PICK)

    def _on_format_changed(self, ext: str) -> None:
        if ext:
            self.settings.setValue("last_format", ext)
        self.btn_go.setEnabled(bool(ext))
        self.btn_go.setText(f"{simple.label_of(ext)}(으)로 변환" if ext else "변환")

    def _search_enter(self) -> None:
        ext = self.grid.first_visible()
        if ext:
            self.grid.select(ext)

    def _reset(self) -> None:
        if self.runner.running:
            return
        self.items.clear()
        self.drop_guide.setText(self.DROP_GUIDE)
        self.stack.setCurrentIndex(PAGE_DROP)

    # ================================================================ 변환
    def _start(self) -> None:
        if not self.ffmpeg:
            self._offer_install()
            return
        target = self.grid.current()
        if not target or not self.items:
            return
        jobs, self._job_files, self._results = [], [], []
        for it in self.items:
            src = it["path"]
            name = Path(src).name
            if not simple.can_convert(it["kind"], simple.ext_of(src), target):
                self._results.append((name, False, "이 형식으로는 바꿀 수 없어요"))
                continue
            out = simple.output_path(src, target)
            args = simple.build_args(self.ffmpeg, src, str(out), target, it["info"], it["kind"])
            jobs.append(Job(args, str(out), it["info"].duration))
            self._job_files.append(it)
        if not jobs:
            QMessageBox.information(self, "알림", "선택한 형식으로 바꿀 수 있는 파일이 없습니다.")
            return
        self._cancelled = False
        self._cur_frac = 0.0
        self.run_title.setText("변환 중...")
        self.run_pct.setText("0%")
        self.run_bar.setValue(0)
        self.run_file.setText("")
        self.run_detail.setText("")
        self.btn_cancel.show()
        self.btn_cancel.setEnabled(True)
        self.btn_open.hide()
        self.btn_again.hide()
        self.stack.setCurrentIndex(PAGE_RUN)
        self.runner.start(jobs)

    def _cancel(self) -> None:
        self._cancelled = True
        self.btn_cancel.setEnabled(False)
        self.run_title.setText("취소하는 중...")
        self.runner.cancel()

    def _on_job_started(self, i: int) -> None:
        self._last_err = ""
        name = Path(self._job_files[i]["path"]).name
        total = len(self._job_files)
        self.run_file.setText(f"{name}  ({i + 1}/{total})")

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
        if not ok and msg.startswith("실패") and self._last_err:
            detail = f"{msg}: {self._last_err[:80]}"
        self._results.append((name, ok, detail))

    def _on_all_finished(self) -> None:
        done = sum(1 for _n, ok, _m in self._results if ok)
        bad = [(n, m) for n, ok, m in self._results if not ok]
        self.btn_cancel.hide()
        self.btn_again.show()
        if done:
            self.btn_open.show()
        if self._cancelled:
            self.run_title.setText("취소되었습니다")
        elif bad and not done:
            self.run_title.setText("변환에 실패했어요")
        else:
            self.run_title.setText("완료!")
            self.run_bar.setValue(1000)
            self.run_pct.setText("100%")
        self.run_file.setText(f"{done}개 변환 완료" + (f" · {len(bad)}개 실패/건너뜀" if bad else ""))
        self.run_detail.setText("\n".join(f"{n}: {m}" for n, m in bad[:5]))

    def _open_folder(self) -> None:
        if self._last_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_dir))

    # ================================================================ ffmpeg 설치
    def _offer_install(self) -> None:
        if self.ffmpeg and self.ffprobe:
            return
        ans = QMessageBox.question(
            self, "ffmpeg 설치",
            "ffmpeg가 없습니다. 지금 자동으로 내려받아 앱 폴더의 bin 에 설치할까요?\n\n"
            "출처: gyan.dev 릴리스 빌드 (약 100MB, GPL 라이선스)\n"
            "다운로드 후 SHA-256 체크섬을 검증합니다.")
        if ans != QMessageBox.Yes:
            return
        self._dlg = QProgressDialog("준비 중...", "취소", 0, 100, self)
        self._dlg.setWindowTitle("ffmpeg 설치")
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
            self._dlg.setLabelText(f"ffmpeg 다운로드 중... {done / 1e6:.0f} / {total / 1e6:.0f} MB")
        else:
            self._dlg.setRange(0, 0)

    def _on_install_ok(self, _folder: str) -> None:
        self._dlg.close()
        self.ffmpeg, self.ffprobe = find_tool("ffmpeg"), find_tool("ffprobe")
        QMessageBox.information(self, "ffmpeg", "설치가 완료되었습니다.")

    def _on_install_failed(self, msg: str) -> None:
        self._dlg.close()
        QMessageBox.warning(self, "ffmpeg 설치 실패", msg)
