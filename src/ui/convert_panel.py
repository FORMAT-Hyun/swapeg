"""형식 변환 도구의 옵션 패널: 바꿀 형식을 상자로 고른다 (검색 가능). OptionPanel 과 같은 방식으로 쓴다."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget

from core import simple, tools
from core.i18n import tr
from ui import icons
from ui.format_grid import FormatGrid


class ConvertPanel(QWidget):
    changed = Signal()                  # 사용자가 형식을 골랐다
    time_edited = Signal()              # (OptionPanel 과 모양을 맞추기 위한 신호, 쓰지 않음)
    add_files_requested = Signal()      # (같음)

    def __init__(self, tool: tools.Tool, preferred: str | None = None, parent=None):
        super().__init__(parent)
        self.tool = tool
        self._quiet = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(8)
        note = QLabel(tr("바꿀 형식을 고르세요. 다른 도구도 같이 체크했다면 편집이 끝난 뒤 이 형식으로 저장돼요."))
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("검색  (예: mp3, 영상, 이미지)"))
        self.search.setClearButtonEnabled(True)
        self.search.addAction(icons.icon("search", icons.MUTED), QLineEdit.LeadingPosition)
        self.grid = FormatGrid()
        self.grid.set_preferred(preferred)
        self.grid.setMinimumHeight(250)
        self.search.textChanged.connect(self.grid.filter)
        self.search.returnPressed.connect(self._enter)
        self.grid.changed.connect(self._on_grid)
        v.addWidget(note)
        v.addWidget(self.search)
        v.addWidget(self.grid, 1)

    # ------------------------------------------------------------ OptionPanel 과 같은 모양
    def values(self) -> dict:
        return {"target": self.grid.current() or ""}

    def set_files(self, items: list[dict]) -> None:
        """넣은 파일들이 바꿀 수 있는 형식만 보여 준다 (같은 형식은 뺀다)."""
        self._quiet = True
        self.search.clear()
        self.grid.rebuild(lambda ext, tk: any(
            simple.can_convert(it["kind"], simple.ext_of(it["path"]), ext, tk) for it in items))
        self._quiet = False

    def set_time(self, _start: str, _end: str) -> None:
        pass

    def file_order(self) -> list[str]:
        return []

    # ------------------------------------------------------------ 내부
    def _on_grid(self, ext: str) -> None:
        if ext and not self._quiet:
            self.changed.emit()

    def _enter(self) -> None:
        ext = self.grid.first_visible()
        if ext:
            self.grid.select(ext)
