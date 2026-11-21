"""미리보기 카드: 파일 썸네일 + 이름(+ 정보)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from core import simple
from core.i18n import tr
from core.thumb import Thumbs


class PreviewCard(QFrame):
    def __init__(self, thumbs: Thumbs, img_size: tuple[int, int] = (220, 140), show_sub: bool = True,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("Preview")
        self._thumbs = thumbs
        self._w, self._h = img_size
        self._expected: str | None = None
        self._pix: QPixmap | None = None
        self.setFixedWidth(self._w + 24)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)
        self.img = QLabel()
        self.img.setObjectName("PreviewImg")
        self.img.setFixedSize(self._w, self._h)
        self.img.setAlignment(Qt.AlignCenter)
        self.name = QLabel()
        self.name.setObjectName("PreviewName")
        self.sub = QLabel()
        self.sub.setObjectName("Muted")
        self.sub.setWordWrap(True)
        self.sub.setVisible(show_sub)
        for w in (self.img, self.name, self.sub):
            v.addWidget(w)
        thumbs.ready.connect(self._on_ready)

    def show_file(self, path: str, name: str, sub: str = "", seek: float = 0.0) -> None:
        self._expected = path
        self._pix = None
        ext = simple.ext_of(path)
        self.img.setPixmap(QPixmap())
        self.img.setText(tr("불러오는 중…"))
        fm = QFontMetrics(self.name.font())
        self.name.setText(fm.elidedText(name, Qt.ElideMiddle, self._w))
        self.name.setToolTip(name)
        self.sub.setText(sub)
        self._ext = ext
        self._thumbs.request(path, seek)

    def _on_ready(self, path: str, data: bytes) -> None:
        if path != self._expected:
            return  # 그 사이 다른 파일로 바뀜
        pix = QPixmap()
        if data and pix.loadFromData(data):
            self.img.setText("")
            self.img.setPixmap(pix.scaled(self._w, self._h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        elif self._ext in simple.AUDIO_EXTS:
            self.img.setText(tr("♪\n오디오"))
        else:
            self.img.setText(tr(".{ext}\n미리보기 없음", ext=self._ext))
