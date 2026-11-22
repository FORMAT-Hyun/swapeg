"""편집 화면 안에서 영상/음악을 재생하는 작은 플레이어 (QtMultimedia).

QtMultimedia 를 못 불러오면 AVAILABLE 이 False 가 되고, 화면은 재생 버튼을 숨긴다.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, QUrl, Signal

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    AVAILABLE = True
except Exception:  # noqa: BLE001 - 플러그인이 없는 환경에서도 앱은 떠야 한다
    QAudioOutput = QMediaPlayer = QVideoWidget = None
    AVAILABLE = False


class Player(QObject):
    position = Signal(float)        # 현재 재생 위치(초)
    playing = Signal(bool)          # 재생 중인지
    stopped = Signal()              # 끝까지 재생되었거나 멈춤 (정지 상태)
    failed = Signal(str)            # 재생할 수 없는 파일

    def __init__(self, video_widget=None, parent=None):
        super().__init__(parent)
        self.path = ""
        self.loaded = False
        self._p = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._audio.setVolume(0.8)
        self._p.setAudioOutput(self._audio)
        if video_widget is not None:
            self._p.setVideoOutput(video_widget)
        self._p.positionChanged.connect(lambda ms: self.position.emit(ms / 1000.0))
        self._p.playbackStateChanged.connect(self._on_state)
        self._p.errorOccurred.connect(lambda _e, msg: self.failed.emit(msg or "error"))

    # ------------------------------------------------------------ 상태
    def _on_state(self, state) -> None:
        self.playing.emit(state == QMediaPlayer.PlayingState)
        if state == QMediaPlayer.StoppedState:
            self.stopped.emit()

    def is_playing(self) -> bool:
        return self._p.playbackState() == QMediaPlayer.PlayingState

    def position_seconds(self) -> float:
        return self._p.position() / 1000.0

    # ------------------------------------------------------------ 제어
    def load(self, path: str) -> None:
        self.path = path
        self.loaded = bool(path)
        self._p.stop()
        self._p.setSource(QUrl.fromLocalFile(path) if path else QUrl())

    def unload(self) -> None:
        """파일을 놓아 준다 (작업이 시작되기 전, 화면을 떠날 때)."""
        self.loaded = False
        self._p.stop()
        self._p.setSource(QUrl())

    def play(self) -> None:
        if self.loaded:
            self._p.play()

    def pause(self) -> None:
        self._p.pause()

    def toggle(self) -> None:
        self.pause() if self.is_playing() else self.play()

    def seek(self, seconds: float) -> None:
        self._p.setPosition(int(max(0.0, seconds) * 1000))
