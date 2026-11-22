"""도구 화면: 미리보기(+구간 막대) / 도구 칩 / 옵션 패널 / 저장 형식 / 실행 버튼."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QHBoxLayout, QLabel, QPushButton, QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from core import simple, tools
from core.i18n import tr
from core.thumb import Thumbs
from ui import icons
from ui.format_dialog import FormatDialog
from ui.format_grid import FlowLayout
from ui.option_panel import OptionPanel
from ui.range_bar import RangeBar

TRIM_TOOLS = ("v_trim", "a_trim")
CROP_TOOLS = ("v_transform", "p_crop")


def fmt_time(sec: float) -> str:
    sec = max(0.0, sec)
    m, s = divmod(sec, 60)
    h, m = divmod(int(m), 60)
    return f"{h}:{m:02d}:{s:04.1f}" if h else f"{m}:{s:04.1f}"


class ImageBox(QLabel):
    """미리보기 이미지 + 크롭 영역 점선 상자."""

    def __init__(self, w: int, h: int):
        super().__init__()
        self.setObjectName("PreviewImg")
        self.setFixedSize(w, h)
        self.setAlignment(Qt.AlignCenter)
        self._media = (0, 0)
        self._crop: tuple | None = None       # ("ratio", r) 또는 ("rect", x, y, w, h)  (원본 픽셀)

    def set_media_size(self, w: int | None, h: int | None) -> None:
        self._media = (w or 0, h or 0)
        self.update()

    def set_crop(self, spec: tuple | None) -> None:
        self._crop = spec
        self.update()

    def paintEvent(self, e) -> None:
        super().paintEvent(e)
        pm = self.pixmap()
        mw, mh = self._media
        if not self._crop or pm is None or pm.isNull() or not mw or not mh:
            return
        k = pm.width() / mw
        ox, oy = (self.width() - pm.width()) / 2, (self.height() - pm.height()) / 2
        if self._crop[0] == "ratio":
            r = self._crop[1]
            cw, ch = (mh * r, mh) if mw / mh > r else (mw, mw / r)
            x, y = (mw - cw) / 2, (mh - ch) / 2
        else:
            _t, x, y, cw, ch = self._crop
        p = QPainter(self)
        p.setPen(QPen(QColor("#2fc9a5"), 2, Qt.DashLine))
        p.setBrush(QColor(47, 201, 165, 40))
        p.drawRect(int(ox + x * k), int(oy + y * k), int(cw * k), int(ch * k))
        p.end()


class ToolPage(QWidget):
    back_requested = Signal()
    settings_requested = Signal()
    about_requested = Signal()
    convert_requested = Signal()
    add_files_requested = Signal()
    run_requested = Signal(object, dict, list, str)    # 도구, 옵션 값, 입력 항목들, 저장 형식(빈 값=원본과 같게)

    def __init__(self, thumbs: Thumbs, parent=None):
        super().__init__(parent)
        self._thumbs = thumbs
        self.module = ""
        self.items: list[dict] = []
        self.tools: list[tools.Tool] = []
        self.panels: list[OptionPanel] = []
        self.cur = 0
        self.out_ext = ""
        self._thumb_path = ""

        v = QVBoxLayout(self)
        v.setContentsMargins(28, 22, 28, 22)
        v.setSpacing(14)

        # --- 위쪽 줄
        top = QHBoxLayout()
        back = QPushButton(tr("처음으로"))
        back.setProperty("ghost", True)
        back.setIcon(icons.icon("back"))
        back.setIconSize(QSize(18, 18))
        back.clicked.connect(self.back_requested)
        self.title_icon = QLabel()
        self.title = QLabel()
        self.title.setObjectName("ToolTitle")
        self.file_lbl = QLabel()
        self.file_lbl.setObjectName("Muted")
        top.addWidget(back)
        top.addWidget(self.title_icon)
        top.addWidget(self.title)
        top.addWidget(self.file_lbl, 1)
        for text, icon, sig in (("정보", "info", self.about_requested), ("설정", "gear", self.settings_requested)):
            b = QPushButton(tr(text))
            b.setProperty("ghost", True)
            b.setIcon(icons.icon(icon))
            b.setIconSize(QSize(18, 18))
            b.clicked.connect(sig)
            top.addWidget(b)
        v.addLayout(top)

        # --- 본문: 미리보기 | 도구
        body = QHBoxLayout()
        body.setSpacing(18)
        left = QVBoxLayout()
        self.image = ImageBox(240, 150)
        self.range = RangeBar()
        self.times = QLabel()
        self.times.setObjectName("Muted")
        self.times.setAlignment(Qt.AlignHCenter)
        left.addWidget(self.image)
        left.addWidget(self.range)
        left.addWidget(self.times)
        left.addStretch(1)
        leftw = QWidget()
        leftw.setFixedWidth(260)
        leftw.setLayout(left)
        body.addWidget(leftw)

        right = QVBoxLayout()
        self.chips = FlowLayout(hspacing=8, vspacing=8)
        chips_holder = QWidget()
        chips_holder.setLayout(self.chips)
        right.addWidget(chips_holder)
        self.stack = QStackedWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(self.stack)
        right.addWidget(scroll, 1)
        body.addLayout(right, 1)
        v.addLayout(body, 1)

        # --- 아래 줄
        bot = QHBoxLayout()
        lab = QLabel(tr("저장 형식"))
        lab.setObjectName("Muted")
        self.fmt_lbl = QPushButton()
        self.fmt_lbl.setProperty("fmt", True)
        self.fmt_lbl.setProperty("compact", True)
        self.fmt_lbl.setCursor(Qt.PointingHandCursor)
        self.fmt_lbl.clicked.connect(self._pick_format)
        self.go = QPushButton()
        self.go.setProperty("primary", True)
        self.go.setIcon(icons.icon("swap", icons.MINT_DARK))
        self.go.setIconSize(QSize(20, 20))
        self.go.setMinimumWidth(150)
        self.go.clicked.connect(self._run)
        bot.addWidget(lab)
        bot.addWidget(self.fmt_lbl)
        bot.addStretch(1)
        bot.addWidget(self.go)
        v.addLayout(bot)

        self.range.rangeChanged.connect(self._on_range_dragged)
        thumbs.ready.connect(self._on_thumb)
        thumbs.peaks_ready.connect(self._on_peaks)

    # ================================================================ 열기
    def open(self, module: str, items: list[dict]) -> None:
        if module != self.module:
            self._build_module(module)
        self.set_items(items)

    def _build_module(self, module: str) -> None:
        self.module = module
        name, icon = tools.MODULES[module]
        self.title.setText(tr(name))
        self.title_icon.setPixmap(icons.pixmap(icon, icons.GREEN, 22, 1.8))
        self.tools = tools.TOOLS[module]
        # 도구 칩 (맨 앞은 형식 변환으로 가는 바로가기)
        while self.chips.count():
            w = self.chips.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.hide()
            w.setParent(None)
            w.deleteLater()
        conv = QPushButton(tr("형식 변환"))
        conv.setProperty("tool", True)
        conv.setProperty("convert", True)
        conv.setIcon(icons.icon("swap"))
        conv.setCursor(Qt.PointingHandCursor)
        conv.clicked.connect(self.convert_requested)
        self.chips.addWidget(conv)
        group = QButtonGroup(self)
        self.panels = []
        self._chip_btns: list[QPushButton] = []
        for i, t in enumerate(self.tools):
            b = QPushButton(tr(t.name))
            b.setProperty("tool", True)
            b.setCheckable(True)
            b.setIcon(icons.icon(t.icon, icons.GREEN))
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=i: self._select_tool(n))
            group.addButton(b)
            self._chip_btns.append(b)
            self.chips.addWidget(b)
            panel = OptionPanel(t)
            panel.changed.connect(self._on_panel_changed)
            panel.time_edited.connect(self._on_time_typed)
            panel.add_files_requested.connect(self.add_files_requested)
            self.stack.addWidget(panel)
            self.panels.append(panel)
        self.cur = 0
        self.out_ext = ""
        self.range.set_interactive(False)
        self._select_tool(0)

    def set_items(self, items: list[dict]) -> None:
        self.items = list(items)
        first = self.items[0]
        name = Path(first["path"]).name
        n = len(self.items)
        self.file_lbl.setText(f"{name}  ·  {first['info'].summary()}" if n == 1
                              else tr("{name} 외 {n}개", name=name, n=n - 1))
        for p in self.panels:
            p.set_files(self.items)
        info = first["info"]
        self.image.set_media_size(info.width, info.height)
        self.range.set_duration(info.duration)
        self.range.set_range(None, None)
        for p in self.panels:
            p.set_time("", "")
        self._thumb_path = first["path"]
        if self.module == "audio":
            self.range.set_peaks([])
            self._thumbs.request_peaks(first["path"])
        else:
            d = info.duration
            self.image.setPixmap(QPixmap())
            self.image.setText(tr("불러오는 중…"))
            self._thumbs.request(first["path"], min(d * 0.2, 10.0) if (self.module == "video" and d) else 0.0)
        self._update_side()

    # ================================================================ 도구 전환
    def _select_tool(self, i: int) -> None:
        self.cur = i
        self._chip_btns[i].setChecked(True)
        self.stack.setCurrentIndex(i)
        self.go.setText(tr(self.tools[i].btn))
        self._update_side()

    def tool(self) -> tools.Tool:
        return self.tools[self.cur]

    def _update_side(self) -> None:
        """도구에 따라 미리보기 쪽 표시를 바꾼다 (구간 막대, 크롭 상자, 파형)."""
        tid = self.tool().id
        audio = self.module == "audio"
        trim = tid in TRIM_TOOLS
        self.image.setVisible(not audio)
        self.range.setMinimumHeight(76 if audio else 28)
        self.range.setVisible(audio or trim)
        self.times.setVisible(audio or trim)
        self.range.set_interactive(trim)
        self._update_crop()
        self._update_times()

    def _on_panel_changed(self) -> None:
        self._update_crop()

    def _update_crop(self) -> None:
        if self.tool().id not in CROP_TOOLS:
            self.image.set_crop(None)
            return
        p = self.panels[self.cur].values()
        ratio = p.get("ratio", "none")
        spec = None
        try:
            if ratio in ("1:1", "4:3", "16:9"):
                a, b = (float(x) for x in ratio.split(":"))
                spec = ("ratio", a / b)
            elif ratio == "custom":
                cw, ch = int(p.get("cw") or 0), int(p.get("ch") or 0)
                if cw > 0 and ch > 0:
                    spec = ("rect", int(p.get("cx") or 0), int(p.get("cy") or 0), cw, ch)
        except ValueError:
            spec = None
        self.image.set_crop(spec)

    # ================================================================ 구간 막대 <-> 시간 입력
    def _on_range_dragged(self, start: float, end: float) -> None:
        dur = self.range._dur
        s = "" if start < 0.05 else fmt_time(start)
        e = "" if dur - end < 0.05 else fmt_time(end)
        for p in self.panels:
            p.set_time(s, e)
        self._update_times()

    def _on_time_typed(self) -> None:
        vals = self.panels[self.cur].values()
        try:
            s, e = tools.parse_time(vals.get("start", "")), tools.parse_time(vals.get("end", ""))
        except tools.ToolError:
            return
        self.range.set_range(s, e)
        self._update_times()

    def _update_times(self) -> None:
        if not self.range._dur:
            self.times.setText("")
            return
        s, e = self.range.range_seconds()
        self.times.setText(f"{fmt_time(s)} – {fmt_time(e)}  ({fmt_time(e - s)})")

    # ================================================================ 미리보기 결과
    def _on_thumb(self, path: str, data: bytes) -> None:
        if path != self._thumb_path or self.module == "audio":
            return
        pm = QPixmap()
        if data and pm.loadFromData(data):
            self.image.setText("")
            self.image.setPixmap(pm.scaled(self.image.width(), self.image.height(),
                                           Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.image.setText(tr(".{ext}\n미리보기 없음", ext=simple.ext_of(path)))
        self.image.update()

    def _on_peaks(self, path: str, peaks) -> None:
        if path == self._thumb_path and self.module == "audio":
            self.range.set_peaks(peaks)

    # ================================================================ 저장 형식 / 실행
    def _refresh_format(self) -> None:
        self.fmt_lbl.setText(simple.label_of(self.out_ext) if self.out_ext else tr("원본과 같은 형식"))

    def _pick_format(self) -> None:
        dlg = FormatDialog(self.module, self.out_ext, self)
        if dlg.exec() and dlg.chosen is not None:
            self.out_ext = dlg.chosen
            self._refresh_format()

    def showEvent(self, e) -> None:
        self._refresh_format()
        super().showEvent(e)

    def _run(self) -> None:
        panel = self.panels[self.cur]
        items = self.items
        if self.tool().multi:                     # 합치기: 목록에 보이는 순서대로
            by_path = {i["path"]: i for i in self.items}
            items = [by_path[p] for p in panel.file_order() if p in by_path]
        self.run_requested.emit(self.tool(), panel.values(), items, self.out_ext)
