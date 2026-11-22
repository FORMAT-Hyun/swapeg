"""도구 사양(core.tools.Tool)으로 옵션 패널을 만든다. 값은 values() 로 한 번에 읽는다."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QSlider, QVBoxLayout, QWidget,
)

from core import tools
from core.i18n import tr
from ui import icons


def _label(text: str) -> QLabel:
    lab = QLabel(tr(text))
    lab.setObjectName("FieldLabel")
    return lab


class OptionPanel(QWidget):
    changed = Signal()                  # 옵션 값이 바뀜
    time_edited = Signal()              # 시작/끝 시간을 직접 입력함 (구간 막대와 맞추는 용도)
    add_files_requested = Signal()      # 합치기: [파일 추가]

    def __init__(self, tool: tools.Tool, parent=None):
        super().__init__(parent)
        self.tool = tool
        self._vals = tools.defaults(tool)
        self._rows: list[tuple[tools.Field, QWidget]] = []
        self._edits: dict[str, QLineEdit] = {}
        self._list: QListWidget | None = None
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(12)
        for f in tool.fields:
            row = getattr(self, f"_build_{f.kind}")(f)
            self._rows.append((f, row))
            v.addWidget(row)
        v.addStretch(1)
        self._refresh()

    # ------------------------------------------------------------ 공개
    def values(self) -> dict:
        return dict(self._vals)

    def set_time(self, start: str, end: str) -> None:
        for key, text in (("start", start), ("end", end)):
            e = self._edits.get(key)
            if e is not None:
                e.setText(text)
                self._vals[key] = text

    def set_files(self, items: list[dict]) -> None:
        if self._list is None:
            return
        self._list.clear()
        for it in items:
            li = QListWidgetItem(Path(it["path"]).name)
            li.setData(Qt.UserRole, it["path"])
            li.setToolTip(it["path"])
            self._list.addItem(li)

    def file_order(self) -> list[str]:
        if self._list is None:
            return []
        return [self._list.item(i).data(Qt.UserRole) for i in range(self._list.count())]

    # ------------------------------------------------------------ 내부
    def _set(self, key: str, value) -> None:
        self._vals[key] = value
        self._refresh()
        self.changed.emit()

    def _refresh(self) -> None:
        for f, row in self._rows:
            row.setVisible(tools.visible(f, self._vals))

    def _line(self, key: str, placeholder: str = "") -> QLineEdit:
        e = QLineEdit(self._vals.get(key, ""))
        e.setPlaceholderText(placeholder)
        e.textChanged.connect(lambda t, k=key: self._set(k, t))
        self._edits[key] = e
        return e

    def _field_box(self, f: tools.Field, *widgets) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(6)
        if f.label:
            v.addWidget(_label(f.label))
        for x in widgets:
            v.addWidget(x) if isinstance(x, QWidget) else v.addLayout(x)
        return w

    # ------------------------------------------------------------ 위젯 종류
    def _build_seg(self, f: tools.Field) -> QWidget:
        row = QHBoxLayout()
        row.setSpacing(6)
        group = QButtonGroup(self)
        for value, text in f.options:
            b = QPushButton(tr(text))
            b.setProperty("seg", True)
            b.setCheckable(True)
            b.setChecked(value == self._vals[f.key])
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, v=value, k=f.key: self._set(k, v))
            group.addButton(b)
            row.addWidget(b)
        row.addStretch(1)
        return self._field_box(f, row)

    def _build_slider(self, f: tools.Field) -> QWidget:
        head = _label(f.label)
        val = QLabel(f"{self._vals[f.key]}{f.unit}")
        val.setObjectName("Muted")
        top = QHBoxLayout()
        top.addWidget(head)
        top.addStretch(1)
        top.addWidget(val)
        s = QSlider(Qt.Horizontal)
        s.setRange(f.min, f.max)
        s.setValue(int(self._vals[f.key]))
        s.valueChanged.connect(lambda x, k=f.key, lab=val, u=f.unit: (lab.setText(f"{x}{u}"), self._set(k, x)))
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        v.addLayout(top)
        v.addWidget(s)
        return w

    def _build_check(self, f: tools.Field) -> QWidget:
        c = QCheckBox()
        c.setChecked(bool(self._vals[f.key]))
        c.toggled.connect(lambda on, k=f.key: self._set(k, on))
        text = QLabel(tr(f.label))                  # 긴 문장은 줄바꿈되도록 라벨을 따로 둔다
        text.setWordWrap(True)
        text.setCursor(Qt.PointingHandCursor)
        text.mousePressEvent = lambda _e: c.toggle()
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(c, 0, Qt.AlignTop)
        row.addWidget(text, 1)
        return w

    def _build_note(self, f: tools.Field) -> QWidget:
        n = QLabel(tr(f.label))
        n.setObjectName("Muted")
        n.setWordWrap(True)
        return n

    def _build_time2(self, f: tools.Field) -> QWidget:
        row = QHBoxLayout()
        for key, name in (("start", "시작"), ("end", "끝")):
            col = QVBoxLayout()
            col.addWidget(_label(name))
            e = self._line(key, "0:00.0")
            e.textEdited.connect(lambda _t: self.time_edited.emit())
            col.addWidget(e)
            row.addLayout(col, 1)
        hint = QLabel(tr("비워 두면 처음부터 / 끝까지입니다. 예: 90, 1:30, 0:01:30"))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        return self._field_box(f, row, hint)

    def _build_size(self, f: tools.Field) -> QWidget:
        row = QHBoxLayout()
        for key, name in (("w", "가로"), ("h", "세로")):
            col = QVBoxLayout()
            col.addWidget(_label(name))
            col.addWidget(self._line(key, "px"))
            row.addLayout(col, 1)
        return self._field_box(f, row)

    def _build_crop(self, f: tools.Field) -> QWidget:
        row = QHBoxLayout()
        for key, name in (("cw", "가로"), ("ch", "세로"), ("cx", "X"), ("cy", "Y")):
            col = QVBoxLayout()
            col.addWidget(_label(name))
            col.addWidget(self._line(key, "px"))
            row.addLayout(col, 1)
        return self._field_box(f, row)

    def _build_pick(self, f: tools.Field) -> QWidget:
        edit = QLineEdit()
        edit.setReadOnly(True)
        edit.setPlaceholderText(tr("파일을 선택하세요"))
        btn = QPushButton(tr("선택"))
        btn.setIcon(icons.icon("folder"))

        def choose():
            path, _ = QFileDialog.getOpenFileName(self, tr(f.pick_title), "", tr(f.pick_filter))
            if path:
                edit.setText(path)
                self._set(f.key, path)

        btn.clicked.connect(choose)
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(btn)
        return self._field_box(f, row)

    def _build_pos9(self, f: tools.Field) -> QWidget:
        grid = QGridLayout()
        grid.setSpacing(4)
        group = QButtonGroup(self)
        for i in range(9):
            b = QPushButton()
            b.setCheckable(True)
            b.setProperty("posbtn", True)
            b.setFixedSize(QSize(34, 24))
            b.setChecked(i == self._vals[f.key])
            b.clicked.connect(lambda _=False, n=i, k=f.key: self._set(k, n))
            group.addButton(b)
            grid.addWidget(b, i // 3, i % 3)
        holder = QHBoxLayout()
        holder.addLayout(grid)
        holder.addStretch(1)
        return self._field_box(f, holder)

    def _build_files(self, f: tools.Field) -> QWidget:
        lst = QListWidget()
        lst.setDragDropMode(QAbstractItemView.InternalMove)
        lst.setDefaultDropAction(Qt.MoveAction)
        lst.setSelectionMode(QAbstractItemView.ExtendedSelection)
        lst.setMinimumHeight(110)
        lst.setMaximumHeight(170)
        self._list = lst
        add = QPushButton(tr("파일 추가"))
        add.setIcon(icons.icon("plus"))
        add.clicked.connect(self.add_files_requested)
        rm = QPushButton(tr("선택 제거"))
        rm.setProperty("ghost", True)
        rm.clicked.connect(lambda: [lst.takeItem(lst.row(i)) for i in lst.selectedItems()])
        row = QHBoxLayout()
        row.addWidget(add)
        row.addWidget(rm)
        row.addStretch(1)
        return self._field_box(f, lst, row)
