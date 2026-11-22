"""QProcess 기반 순차 작업 큐. -progress 출력을 파싱해 진행률을 알린다."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from .i18n import tr


@dataclass
class Job:
    args: list[str]
    output: str
    duration: float | None = None   # 출력 예상 길이(초)
    log: list[str] = field(default_factory=list)
    prepare: Callable[["Job"], None] | None = None   # 실행 직전에 args/duration 을 채운다 (실패하면 예외)


class JobRunner(QObject):
    job_started = Signal(int)
    progress = Signal(int, float)          # index, 0.0~1.0
    log = Signal(str)
    job_finished = Signal(int, bool, str)  # index, 성공, 메시지
    all_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._jobs: list[Job] = []
        self._i = -1
        self._proc: QProcess | None = None
        self._buf = ""
        self._cancelled = False
        self.running = False

    def start(self, jobs: list[Job]) -> None:
        if self.running:
            return
        self._jobs, self._i, self._cancelled, self.running = jobs, -1, False, True
        self._next()

    def cancel(self) -> None:
        if not self.running:
            return
        self._cancelled = True
        p = self._proc
        if p and p.state() != QProcess.NotRunning:
            p.write(b"q")  # ffmpeg 정상 종료 요청
            QTimer.singleShot(1500, lambda: p.state() != QProcess.NotRunning and p.kill())

    # ------------------------------------------------------------------
    def _next(self) -> None:
        self._i += 1
        if self._cancelled or self._i >= len(self._jobs):
            self.running = False
            self.all_finished.emit()
            return
        job = self._jobs[self._i]
        self._buf = ""
        self.job_started.emit(self._i)
        if job.prepare:                      # 앞 단계 결과를 보고 명령을 만드는 단계
            try:
                job.prepare(job)
            except Exception as e:           # noqa: BLE001 - 사유를 화면에 그대로 보여 준다
                self._proc = None
                self.job_finished.emit(self._i, False, str(e) or tr("실패"))
                QTimer.singleShot(0, self._next)
                return
        p = QProcess(self)
        self._proc = p
        p.readyReadStandardOutput.connect(self._on_stdout)
        p.readyReadStandardError.connect(self._on_stderr)
        p.finished.connect(self._on_finished)
        p.errorOccurred.connect(self._on_error)
        self.log.emit(f"\n[{self._i + 1}/{len(self._jobs)}] 시작")
        p.start(job.args[0], job.args[1:])

    def _on_stdout(self) -> None:
        self._buf += bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        *lines, self._buf = self._buf.split("\n")
        job = self._jobs[self._i]
        for line in lines:
            key, _, val = line.strip().partition("=")
            if key in ("out_time_us", "out_time_ms") and job.duration:
                try:
                    sec = int(val) / 1_000_000
                except ValueError:
                    continue
                self.progress.emit(self._i, max(0.0, min(sec / job.duration, 1.0)))

    def _on_stderr(self) -> None:
        text = bytes(self._proc.readAllStandardError()).decode("utf-8", "replace")
        self.log.emit(text.rstrip())

    def _on_error(self, err) -> None:
        if err == QProcess.FailedToStart:
            self.log.emit(tr("ffmpeg 실행에 실패했습니다."))

    def _on_finished(self, code: int, _status) -> None:
        idx, job = self._i, self._jobs[self._i]
        if self._cancelled:
            Path(job.output).unlink(missing_ok=True)
            self.job_finished.emit(idx, False, tr("취소됨"))
        elif code == 0:
            self.progress.emit(idx, 1.0)
            self.job_finished.emit(idx, True, tr("완료"))
        else:
            Path(job.output).unlink(missing_ok=True)
            self.job_finished.emit(idx, False, tr("실패 (코드 {code})", code=code))
        self._proc.deleteLater()
        self._next()
