from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QProgressDialog, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from core import simple
from core.ffpath import app_dir, find_tool
from core.installer import InstallWorker
from core.probe import MediaInfo, probe
from core.runner import Job, JobRunner

FILE_FILTER = ("미디어/이미지 (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.gif "
               "*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma "
               "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff *.ico);;모든 파일 (*.*)")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FFmpeg 변환기")
        self.resize(760, 560)
        self.setAcceptDrops(True)

        self.ffmpeg = find_tool("ffmpeg")
        self.ffprobe = find_tool("ffprobe")
        self.items: list[dict] = []        # {path, info, kind}
        self._job_rows: list[int] = []
        self._last_err = ""
        self._last_dir = ""

        self.runner = JobRunner(self)
        self.runner.job_started.connect(self._on_job_started)
        self.runner.progress.connect(self._on_progress)
        self.runner.log.connect(self._remember_log)
        self.runner.job_finished.connect(self._on_job_finished)
        self.runner.all_finished.connect(self._on_all_finished)

        self._build_ui()
        self._refresh_formats()
        if not self.ffmpeg or not self.ffprobe:
            QTimer.singleShot(300, self._offer_install)

    # ---------------------------------------------------------------- UI
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        v = QVBoxLayout(root)
        v.setContentsMargins(24, 20, 24, 20)
        v.setSpacing(12)

        title = QLabel("FFmpeg 변환기")
        title.setObjectName("Title")
        sub = QLabel("파일을 넣고, 바꿀 형식을 고른 뒤 [바꾸기]를 누르세요. 화질은 원본 그대로 유지됩니다.")
        sub.setObjectName("Muted")
        v.addWidget(title)
        v.addWidget(sub)

        self.stack = QStackedWidget()
        self.drop = QPushButton("여기에 파일을 끌어다 놓거나\n눌러서 파일을 선택하세요")
        self.drop.setObjectName("DropZone")
        self.drop.setCursor(Qt.PointingHandCursor)
        self.drop.clicked.connect(self._add_dialog)
        self.stack.addWidget(self.drop)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["파일", "정보", "상태"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.stack.addWidget(self.table)
        v.addWidget(self.stack, 1)

        row = QHBoxLayout()
        b_add = QPushButton("파일 추가")
        b_add.clicked.connect(self._add_dialog)
        self.b_clear = QPushButton("비우기")
        self.b_clear.setProperty("ghost", True)
        self.b_clear.clicked.connect(self._clear)
        self.b_open = QPushButton("폴더 열기")
        self.b_open.setProperty("ghost", True)
        self.b_open.clicked.connect(self._open_folder)
        self.b_open.hide()
        row.addWidget(b_add)
        row.addWidget(self.b_clear)
        row.addWidget(self.b_open)
        row.addStretch()
        lab = QLabel("바꿀 형식")
        lab.setObjectName("Muted")
        self.fmt = QComboBox()
        self.fmt.setMinimumWidth(170)
        self.btn_go = QPushButton("바꾸기")
        self.btn_go.setProperty("primary", True)
        self.btn_go.setMinimumWidth(110)
        self.btn_go.clicked.connect(self._start)
        self.btn_cancel = QPushButton("취소")
        self.btn_cancel.clicked.connect(self.runner.cancel)
        self.btn_cancel.hide()
        row.addWidget(lab)
        row.addWidget(self.fmt)
        row.addWidget(self.btn_go)
        row.addWidget(self.btn_cancel)
        v.addLayout(row)

        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        v.addWidget(self.bar)
        self.status = QLabel("")
        self.status.setObjectName("Muted")
        v.addWidget(self.status)

    # ------------------------------------------------------------ 형식 목록
    def _refresh_formats(self) -> None:
        prev = self.fmt.currentData()
        self.fmt.clear()
        for ext, label, _k in simple.FORMATS:
            if not self.items or any(simple.can_convert(it["kind"], simple.ext_of(it["path"]), ext)
                                     for it in self.items):
                self.fmt.addItem(label, ext)
        i = self.fmt.findData(prev)
        self.fmt.setCurrentIndex(i if i >= 0 else 0)

    # -------------------------------------------------------------- 파일
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        self._add_files([u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()])

    def _add_dialog(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "파일 선택", self._last_dir, FILE_FILTER)
        self._add_files(paths)

    def _add_files(self, paths: list[str]) -> None:
        if self.runner.running:
            return
        for p in paths:
            if not Path(p).is_file() or any(it["path"] == p for it in self.items):
                continue
            info = probe(self.ffprobe, p) if self.ffprobe else MediaInfo()
            kind = simple.kind_of(p, info)
            self.items.append({"path": p, "info": info, "kind": kind})
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(Path(p).name))
            self.table.setItem(r, 1, QTableWidgetItem(info.summary()))
            self.table.setItem(r, 2, QTableWidgetItem("대기"))
            self.table.item(r, 0).setToolTip(p)
            self._last_dir = str(Path(p).parent)
        self.stack.setCurrentIndex(1 if self.items else 0)
        self._refresh_formats()
        self.b_open.hide()
        self.status.setText(f"{len(self.items)}개 파일" if self.items else "")

    def _clear(self) -> None:
        if self.runner.running:
            return
        self.table.setRowCount(0)
        self.items.clear()
        self.stack.setCurrentIndex(0)
        self.bar.setValue(0)
        self.status.setText("")
        self.b_open.hide()
        self._refresh_formats()

    def _open_folder(self) -> None:
        if self._last_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_dir))

    # -------------------------------------------------------------- 실행
    def _set_status(self, row: int, text: str) -> None:
        if 0 <= row < self.table.rowCount():
            self.table.setItem(row, 2, QTableWidgetItem(text))

    def _start(self) -> None:
        if not self.ffmpeg:
            self._offer_install()
            return
        if not self.items:
            self._add_dialog()
            return
        target = self.fmt.currentData()
        jobs, self._job_rows = [], []
        for r, it in enumerate(self.items):
            src = it["path"]
            if not simple.can_convert(it["kind"], simple.ext_of(src), target):
                self._set_status(r, "이 형식으로는 바꿀 수 없어요")
                continue
            out = simple.output_path(src, target)
            args = simple.build_args(self.ffmpeg, src, str(out), target, it["info"], it["kind"])
            jobs.append(Job(args, str(out), it["info"].duration))
            self._job_rows.append(r)
            self._set_status(r, "대기")
        if not jobs:
            QMessageBox.information(self, "알림", "선택한 형식으로 바꿀 수 있는 파일이 없습니다.")
            return
        self._done = self._failed = 0
        self.bar.setValue(0)
        self.b_open.hide()
        self.btn_go.setEnabled(False)
        self.btn_cancel.show()
        self.runner.start(jobs)

    def _on_job_started(self, i: int) -> None:
        self._last_err = ""
        self._set_status(self._job_rows[i], "변환 중...")
        self.status.setText(f"변환 중 ({i + 1}/{len(self._job_rows)})")

    def _on_progress(self, i: int, frac: float) -> None:
        self.bar.setValue(int(frac * 1000))
        self._set_status(self._job_rows[i], f"{frac * 100:.0f}%")

    def _remember_log(self, text: str) -> None:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            self._last_err = lines[-1]

    def _on_job_finished(self, i: int, ok: bool, msg: str) -> None:
        row = self._job_rows[i]
        if ok:
            self._done += 1
            self._set_status(row, "완료 ✓")
        else:
            self._failed += 1
            detail = f": {self._last_err[:70]}" if msg.startswith("실패") and self._last_err else ""
            self._set_status(row, msg + detail)

    def _on_all_finished(self) -> None:
        self.btn_go.setEnabled(True)
        self.btn_cancel.hide()
        text = f"완료 {self._done}개"
        if self._failed:
            text += f" · 실패/취소 {self._failed}개"
        self.status.setText(text)
        if self._done:
            self.b_open.show()

    # ---------------------------------------------------------- ffmpeg 설치
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
