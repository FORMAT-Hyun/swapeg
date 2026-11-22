"""저장 형식 고르기 창: 모듈에서 쓸 수 있는 형식만 상자로 보여 준다."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout

from core import tools
from core.i18n import tr
from ui import icons
from ui.format_grid import FormatGrid


class FormatDialog(QDialog):
    def __init__(self, module: str, current: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("저장 형식"))
        self.resize(560, 460)
        self.chosen: str | None = None        # None: 취소, "": 원본과 같은 형식, 그 외: 확장자
        allowed = tools.MODULE_EXTS[module]
        kind = tools.MODULE_KIND[module]

        v = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("검색  (예: mp3, 영상, 이미지)"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icons.icon("search", icons.MUTED), QLineEdit.LeadingPosition)
        v.addWidget(self.search)

        self.grid = FormatGrid()
        self.grid.set_preferred(current or None)
        self.grid.rebuild(lambda ext, tk: ext in allowed and tk == kind)
        self.search.textChanged.connect(self.grid.filter)
        v.addWidget(self.grid, 1)

        row = QHBoxLayout()
        same = QPushButton(tr("원본과 같은 형식"))
        same.clicked.connect(lambda: self._finish(""))
        cancel = QPushButton(tr("취소"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("선택"))
        ok.setProperty("primary", True)
        ok.clicked.connect(lambda: self._finish(self.grid.current() or ""))
        row.addWidget(same)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(ok)
        v.addLayout(row)

    def _finish(self, ext: str) -> None:
        self.chosen = ext
        self.accept()
