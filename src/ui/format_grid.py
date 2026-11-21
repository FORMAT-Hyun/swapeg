"""형식 선택 화면: 모든 출력 형식을 상자(버튼)로 나열하고, 검색으로 거를 수 있다."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (QButtonGroup, QLabel, QLayout, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from core import simple


class FlowLayout(QLayout):
    """위젯을 왼쪽에서 오른쪽으로 놓다가 폭이 모자라면 다음 줄로 내리는 레이아웃."""

    def __init__(self, parent=None, hspacing: int = 10, vspacing: int = 10):
        super().__init__(parent)
        self._items = []
        self._h, self._v = hspacing, vspacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._layout(QRect(0, 0, width, 0), dry=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._layout(rect, dry=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for it in self._items:
            if not it.isEmpty():
                size = size.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _layout(self, rect: QRect, dry: bool) -> int:
        m = self.contentsMargins()
        r = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = r.x(), r.y(), 0
        for it in self._items:
            if it.isEmpty():  # 숨겨진 위젯은 자리를 차지하지 않는다
                continue
            hint = it.sizeHint()
            if x + hint.width() > r.right() + 1 and line_h > 0:
                x = r.x()
                y += line_h + self._v
                line_h = 0
            if not dry:
                it.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._h
            line_h = max(line_h, hint.height())
        return y + line_h - rect.y() + m.bottom()


class _Section:
    def __init__(self, kind: str, header: QLabel, flow: FlowLayout, box: QWidget):
        self.kind, self.header, self.flow, self.box = kind, header, flow, box
        self.chips: dict[str, QPushButton] = {}


class FormatGrid(QScrollArea):
    changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._inner = QWidget()
        self._inner.setObjectName("GridInner")
        self._lay = QVBoxLayout(self._inner)
        self._lay.setContentsMargins(0, 0, 8, 0)
        self._lay.setSpacing(14)
        self._lay.addStretch(1)
        self.setWidget(self._inner)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._sections: list[_Section] = []
        self._current: str | None = None
        self._preferred: str | None = None

    # ------------------------------------------------------------ 상태
    def current(self) -> str | None:
        return self._current

    def set_preferred(self, ext: str | None) -> None:
        self._preferred = ext

    def select(self, ext: str) -> None:
        for s in self._sections:
            if ext in s.chips:
                s.chips[ext].setChecked(True)
                self._current = self._preferred = ext
                self.changed.emit(ext)
                return

    # ------------------------------------------------------------ 구성
    def rebuild(self, allowed: Callable[[str, str], bool]) -> None:
        """allowed(ext, kind) 가 True 인 형식만 상자로 보여 준다. 이전 선택이 남아 있으면 유지."""
        prev = self._current or self._preferred
        for s in self._sections:
            self._lay.removeWidget(s.box)
            s.box.hide()
            s.box.setParent(None)
            s.box.deleteLater()
        self._sections = []
        for b in list(self._group.buttons()):
            self._group.removeButton(b)

        by_kind: dict[str, list[str]] = {}
        for ext, _label, kind in simple.FORMATS:
            if allowed(ext, kind):
                by_kind.setdefault(kind, []).append(ext)

        for kind, exts in by_kind.items():
            box = QWidget()
            v = QVBoxLayout(box)
            v.setContentsMargins(0, 0, 0, 0)
            v.setSpacing(8)
            header = QLabel(simple.KIND_TITLE[kind])
            header.setObjectName("SectionLabel")
            v.addWidget(header)
            flow = FlowLayout()
            v.addLayout(flow)
            sec = _Section(kind, header, flow, box)
            popular = [e for e in simple.POPULAR[kind] if e in exts]
            for ext in popular + [e for e in exts if e not in popular]:
                b = QPushButton(simple.label_of(ext))
                b.setProperty("fmt", True)
                b.setCheckable(True)
                b.setCursor(Qt.PointingHandCursor)
                b.setToolTip(f".{ext}")
                self._group.addButton(b)
                b.clicked.connect(lambda _=False, e=ext: self._on_click(e))
                flow.addWidget(b)
                sec.chips[ext] = b
            self._lay.insertWidget(self._lay.count() - 1, box)
            self._sections.append(sec)

        chips = {e: b for s in self._sections for e, b in s.chips.items()}
        pick = prev if prev in chips else None
        if pick is None and by_kind:
            default = simple.DEFAULT[next(iter(by_kind))]
            pick = default if default in chips else next(iter(chips))
        self._current = pick
        if pick:
            chips[pick].setChecked(True)
        self.changed.emit(pick or "")

    def _on_click(self, ext: str) -> None:
        self._current = self._preferred = ext
        self.changed.emit(ext)

    # ------------------------------------------------------------ 검색
    def filter(self, text: str) -> None:
        t = text.strip().lower().lstrip(".")
        for s in self._sections:
            any_visible = False
            for ext, b in s.chips.items():
                hay = f"{ext} {simple.label_of(ext)} {simple.KIND_TITLE[s.kind]}".lower()
                show = not t or t in hay
                b.setVisible(show)
                any_visible |= show
            s.box.setVisible(any_visible)
            s.flow.invalidate()

    def first_visible(self) -> str | None:
        for s in self._sections:
            for ext, b in s.chips.items():
                if not b.isHidden() and not s.box.isHidden():
                    return ext
        return None
