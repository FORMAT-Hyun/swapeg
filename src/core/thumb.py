"""ffmpeg로 미리보기용 썸네일(PNG) 한 장을 뽑는다. UI가 멈추지 않도록 스레드풀에서 실행."""
from __future__ import annotations

import subprocess
import sys
from array import array
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal


def grab_thumbnail(ffmpeg: str, path: str, seek: float = 0.0, width: int = 640) -> bytes:
    """영상/이미지/오디오 커버에서 한 프레임을 PNG 바이트로. 없으면 빈 바이트."""
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

    def run(with_seek: bool) -> bytes:
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
        if with_seek and seek > 0:
            cmd += ["-ss", f"{seek:.2f}"]
        cmd += ["-i", path, "-map", "0:v:0?", "-frames:v", "1",
                "-vf", f"scale='min({width},iw)':-2", "-f", "image2pipe", "-vcodec", "png", "-"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=25, creationflags=flags)
        except (OSError, subprocess.SubprocessError):
            return b""
        return r.stdout if r.returncode == 0 and len(r.stdout) > 100 else b""

    data = run(True)
    if not data and seek > 0:  # 너무 짧은 영상이면 처음 프레임으로 다시 시도
        data = run(False)
    return data


def grab_peaks(ffmpeg: str, path: str, bins: int = 200) -> list[float]:
    """오디오를 저해상도로 읽어 막대 파형용 최대값(0~1) 목록을 만든다. 읽을 수 없으면 빈 목록."""
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    cmd = [ffmpeg, "-v", "error", "-nostdin", "-i", path, "-vn", "-ac", "1", "-ar", "4000", "-f", "s16le", "-"]
    try:
        raw = subprocess.run(cmd, capture_output=True, timeout=120, creationflags=flags).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    a = array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    if not a:
        return []
    step = max(1, len(a) // bins)
    peaks = [max(max(a[i:i + step]), -min(a[i:i + step])) for i in range(0, len(a), step)][:bins]
    top = max(peaks) or 1
    return [p / top for p in peaks]


class _Signals(QObject):
    done = Signal(str, bytes)
    peaks = Signal(str, object)

class _Task(QRunnable):
    def __init__(self, ffmpeg: str, path: str, seek: float, signals: _Signals):
        super().__init__()
        self.ffmpeg, self.path, self.seek, self.signals = ffmpeg, path, seek, signals

    def run(self) -> None:
        data = grab_thumbnail(self.ffmpeg, self.path, self.seek)
        try:
            self.signals.done.emit(self.path, data)
        except RuntimeError:
            pass  # 그 사이 앱이 종료되어 신호 객체가 사라진 경우


class _PeakTask(QRunnable):
    def __init__(self, ffmpeg: str, path: str, signals: _Signals):
        super().__init__()
        self.ffmpeg, self.path, self.signals = ffmpeg, path, signals

    def run(self) -> None:
        data = grab_peaks(self.ffmpeg, self.path)
        try:
            self.signals.peaks.emit(self.path, data)
        except RuntimeError:
            pass


class Thumbs(QObject):
    """request(path) 하면 잠시 뒤 ready(path, png바이트)가 온다. 바이트가 비어 있으면 미리볼 수 없는 파일."""
    ready = Signal(str, bytes)
    peaks_ready = Signal(str, object)   # 오디오 파형: (경로, 0~1 값 목록)

    def __init__(self, ffmpeg_getter: Callable[[], str | None], parent=None):
        super().__init__(parent)
        self._ffmpeg = ffmpeg_getter
        self._cache: dict[str, bytes] = {}
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.peaks.connect(self.peaks_ready)
        self._peak_cache: dict[str, list[float]] = {}
        self._signals.peaks.connect(self._on_peaks)

    def request(self, path: str, seek: float = 0.0) -> None:
        if path in self._cache:
            data = self._cache[path]
            QTimer.singleShot(0, lambda: self.ready.emit(path, data))
            return
        ff = self._ffmpeg()
        if not ff:
            QTimer.singleShot(0, lambda: self.ready.emit(path, b""))
            return
        QThreadPool.globalInstance().start(_Task(ff, path, seek, self._signals))

    def request_peaks(self, path: str) -> None:
        if path in self._peak_cache:
            data = self._peak_cache[path]
            QTimer.singleShot(0, lambda: self.peaks_ready.emit(path, data))
            return
        ff = self._ffmpeg()
        if not ff:
            QTimer.singleShot(0, lambda: self.peaks_ready.emit(path, []))
            return
        QThreadPool.globalInstance().start(_PeakTask(ff, path, self._signals))

    def _on_peaks(self, path: str, data) -> None:
        if data:
            self._peak_cache[path] = data

    def _on_done(self, path: str, data: bytes) -> None:
        if data:
            self._cache[path] = data
        self.ready.emit(path, data)
