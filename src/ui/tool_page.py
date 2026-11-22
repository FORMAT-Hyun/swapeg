"""도구 화면: 미리보기·재생(+구간 막대) / 도구 칩(체크박스) / 옵션 패널 / 저장 형식 / 실행 버튼.

체크한 도구들은 정해진 순서로 이어서 한 번에 적용된다 (core.tools.plan_chain).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider, QStackedWidget,
    QStyle, QVBoxLayout, QWidget,
)

from core import simple, tools
from core.i18n import tr
from core.thumb import Thumbs
from ui import icons, player as media
from ui.format_dialog import FormatDialog
from ui.format_grid import FlowLayout
from ui.option_panel import OptionPanel
from ui.range_bar import RangeBar

TRIM_TOOLS = ("v_trim", "a_trim")
MERGE_TOOLS = ("v_merge", "a_merge")
CROP_TOOLS = ("v_transform", "p_crop")
VIEW_W, VIEW_H = 300, 170


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


class SeekSlider(QSlider):
    """누른 자리로 바로 이동하고 끌 수 있는 재생 위치 슬라이더 (0~1000)."""
    seeked = Signal(float)      # 0~1

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.setRange(0, 1000)

    def _frac(self, x: float) -> float:
        return QStyle.sliderValueFromPosition(0, 1000, int(x), max(self.width(), 1)) / 1000.0

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self.setValue(int(self._frac(e.position().x()) * 1000))
            self.seeked.emit(self.value() / 1000.0)
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e) -> None:
        super().mouseMoveEvent(e)
        if self.isSliderDown():
            self.seeked.emit(self.value() / 1000.0)


class ToolChip(QFrame):
    """[체크박스] 도구 이름. 이름을 누르면 옵션을 보고, 체크하면 이번 작업에 포함한다."""
    selected = Signal()
    toggled = Signal(bool)

    def __init__(self, text: str, icon_name: str):
        super().__init__()
        self.setProperty("chip", True)
        self.setProperty("on", False)
        self.setProperty("viewing", False)
        h = QHBoxLayout(self)
        h.setContentsMargins(10, 3, 12, 3)
        h.setSpacing(4)
        self.check = QCheckBox()
        self.check.setCursor(Qt.PointingHandCursor)
        self.check.setToolTip(tr("이 도구를 적용"))
        self.check.toggled.connect(self._on_toggled)
        self.btn = QPushButton(text)
        self.btn.setIcon(icons.icon(icon_name, icons.GREEN))
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self.selected)
        h.addWidget(self.check)
        h.addWidget(self.btn)

    def is_checked(self) -> bool:
        return self.check.isChecked()

    def set_checked(self, on: bool) -> None:
        self.check.setChecked(on)

    def set_viewing(self, on: bool) -> None:
        self._flag("viewing", on)

    def _on_toggled(self, on: bool) -> None:
        self._flag("on", on)
        self.toggled.emit(on)

    def _flag(self, name: str, value: bool) -> None:
        self.setProperty(name, value)
        self.style().unpolish(self)
        self.style().polish(self)


class ToolPage(QWidget):
    back_requested = Signal()
    settings_requested = Signal()
    about_requested = Signal()
    convert_requested = Signal()
    add_files_requested = Signal()
    run_requested = Signal(list, list, str)    # [(도구, 옵션 값)], 입력 항목들, 저장 형식(빈 값=원본과 같게)

    def __init__(self, thumbs: Thumbs, parent=None):
        super().__init__(parent)
        self._thumbs = thumbs
        self.module = ""
        self.items: list[dict] = []
        self.tools: list[tools.Tool] = []
        self.panels: list[OptionPanel] = []
        self.chips: list[ToolChip] = []
        self.cur = 0
        self.out_ext = ""
        self._thumb_path = ""
        self._pi = 0                          # 미리 보는 파일 번호
        self._peaks: list[float] = []
        self._loading = False

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
        left.setSpacing(8)
        self.preview_pick = QComboBox()                    # 여러 파일일 때 어느 파일을 볼지
        self.preview_pick.currentIndexChanged.connect(self._on_preview_pick)
        self.image = ImageBox(VIEW_W, VIEW_H)
        self.video = media.QVideoWidget() if media.AVAILABLE else None
        self.view = QStackedWidget()
        self.view.setFixedSize(VIEW_W, VIEW_H)
        self.view.addWidget(self.image)
        if self.video is not None:
            self.video.setStyleSheet("background: #111;")
            self.view.addWidget(self.video)
        self.range = RangeBar()
        self.times = QLabel()
        self.times.setObjectName("Muted")
        self.times.setAlignment(Qt.AlignHCenter)
        left.addWidget(self.preview_pick)
        left.addWidget(self.view)
        left.addWidget(self.range)
        left.addWidget(self.times)

        # 재생 막대: [재생] ----o---- 0:12 / 1:30
        self.controls = QWidget()
        ctl = QHBoxLayout(self.controls)
        ctl.setContentsMargins(0, 0, 0, 0)
        ctl.setSpacing(8)
        self.play_btn = QPushButton()
        self.play_btn.setProperty("ghost", True)
        self.play_btn.setIcon(icons.icon("play"))
        self.play_btn.setIconSize(QSize(22, 22))
        self.play_btn.setFixedSize(36, 32)
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setToolTip(tr("재생 / 일시정지"))
        self.seek = SeekSlider()
        self.pos_lbl = QLabel("0:00.0 / 0:00.0")
        self.pos_lbl.setObjectName("Muted")
        ctl.addWidget(self.play_btn)
        ctl.addWidget(self.seek, 1)
        ctl.addWidget(self.pos_lbl)
        left.addWidget(self.controls)

        # 자르기: 지금 재생 위치를 시작/끝으로
        self.mark_row = QWidget()
        mk = QHBoxLayout(self.mark_row)
        mk.setContentsMargins(0, 0, 0, 0)
        self.mark_in = QPushButton(tr("여기부터"))
        self.mark_out = QPushButton(tr("여기까지"))
        for b in (self.mark_in, self.mark_out):
            b.setCursor(Qt.PointingHandCursor)
            mk.addWidget(b)
        left.addWidget(self.mark_row)
        self.note = QLabel()
        self.note.setObjectName("Muted")
        self.note.setWordWrap(True)
        left.addWidget(self.note)
        self.play_err = QLabel()
        self.play_err.setObjectName("Error")
        self.play_err.setWordWrap(True)
        left.addWidget(self.play_err)
        left.addStretch(1)
        leftw = QWidget()
        leftw.setFixedWidth(VIEW_W + 20)
        leftw.setLayout(left)
        body.addWidget(leftw)

        right = QVBoxLayout()
        self.chip_flow = FlowLayout(hspacing=8, vspacing=8)
        chips_holder = QWidget()
        chips_holder.setLayout(self.chip_flow)
        right.addWidget(chips_holder)
        hint = QLabel(tr("체크한 도구는 정해진 순서대로 한 번에 적용돼요. 옵션을 바꾸면 자동으로 체크됩니다."))
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        right.addWidget(hint)
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

        # --- 재생
        self.player: media.Player | None = None
        if media.AVAILABLE:
            self.player = media.Player(self.video, self)
            self.player.position.connect(self._on_position)
            self.player.playing.connect(self._on_playing)
            self.player.stopped.connect(self._on_stopped)
            self.player.failed.connect(self._on_play_failed)
            self.play_btn.clicked.connect(self._toggle_play)
            self.seek.seeked.connect(self._on_seeked)
        self.mark_in.clicked.connect(lambda: self._mark(True))
        self.mark_out.clicked.connect(lambda: self._mark(False))

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
        while self.chip_flow.count():
            w = self.chip_flow.takeAt(0).widget()
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
        self.chip_flow.addWidget(conv)
        self.panels, self.chips = [], []
        for i, t in enumerate(self.tools):
            chip = ToolChip(tr(t.name), t.icon)
            chip.selected.connect(lambda n=i: self._on_chip_clicked(n))
            chip.toggled.connect(lambda on, n=i: self._on_check_toggled(n, on))
            self.chip_flow.addWidget(chip)
            self.chips.append(chip)
            panel = OptionPanel(t)
            panel.changed.connect(lambda n=i: self._on_panel_changed(n))
            panel.time_edited.connect(self._on_time_typed)
            panel.add_files_requested.connect(self.add_files_requested)
            self.stack.addWidget(panel)
            self.panels.append(panel)
        self.cur = 0
        self.out_ext = ""
        self.range.set_interactive(False)
        self._select_tool(0)

    def set_items(self, items: list[dict]) -> None:
        self._loading = True                  # 파일을 다시 채우는 동안에는 자동 체크를 하지 않는다
        self.items = list(items)
        first = self.items[0]
        name = Path(first["path"]).name
        n = len(self.items)
        self.file_lbl.setText(f"{name}  ·  {first['info'].summary()}" if n == 1
                              else tr("{name} 외 {n}개", name=name, n=n - 1))
        for p in self.panels:
            p.set_files(self.items)
        self.range.set_range(None, None)
        for p in self.panels:
            p.set_time("", "")
        self.preview_pick.blockSignals(True)
        self.preview_pick.clear()
        for it in self.items:
            self.preview_pick.addItem(Path(it["path"]).name)
        self.preview_pick.blockSignals(False)
        self.preview_pick.setVisible(n > 1 and self.module != "photo")
        self._loading = False
        self._load_preview(0)

    def _load_preview(self, i: int) -> None:
        self._pi = i
        it = self.items[i]
        info, path = it["info"], it["path"]
        self._thumb_path = path
        self._peaks = []
        self.image.set_media_size(info.width, info.height)
        if self.module == "audio":
            self._thumbs.request_peaks(path)
        else:
            d = info.duration
            self.image.setPixmap(QPixmap())
            self.image.setText(tr("불러오는 중…"))
            self._thumbs.request(path, min(d * 0.2, 10.0) if (self.module == "video" and d) else 0.0)
        if self.player is not None and self.module in ("video", "audio"):
            self.player.load(path)
        self.view.setCurrentIndex(0)
        self.pos_lbl.setText(f"0:00.0 / {fmt_time(info.duration or 0)}")
        self.seek.setValue(0)
        self.play_err.setText("")
        self.play_btn.setEnabled(True)
        self._refresh_range_source()
        self._update_side()

    def _on_preview_pick(self, i: int) -> None:
        if 0 <= i < len(self.items):
            self._load_preview(i)

    # ================================================================ 도구 선택(보기) / 체크(적용)
    def _checked_idx(self) -> list[int]:
        return [i for i, c in enumerate(self.chips) if c.is_checked()]

    def _is_checked(self, ids: tuple) -> bool:
        return any(self.chips[i].is_checked() for i, t in enumerate(self.tools) if t.id in ids)

    def _select_tool(self, i: int) -> None:
        self.cur = i
        for k, c in enumerate(self.chips):
            c.set_viewing(k == i)
        self.stack.setCurrentIndex(i)
        self._update_run()
        self._update_side()

    def _on_chip_clicked(self, i: int) -> None:
        self._select_tool(i)
        if not self._checked_idx():           # 아직 아무것도 체크 안 했다면 처음 연 도구를 적용 대상으로
            self.chips[i].set_checked(True)

    def _on_check_toggled(self, i: int, on: bool) -> None:
        if on:
            self._select_tool(i)
        self._update_run()
        self._refresh_range_source()
        self._update_side()

    def _on_panel_changed(self, i: int) -> None:
        if not self._loading and not self.chips[i].is_checked():
            self.chips[i].set_checked(True)   # 옵션을 만졌으면 그 도구를 쓰려는 것
        self._update_crop()

    def _update_run(self) -> None:
        ids = self._checked_idx()
        self.go.setEnabled(bool(ids))
        if not ids:
            self.go.setText(tr("도구를 체크해 주세요"))
        elif len(ids) == 1:
            self.go.setText(tr(self.tools[ids[0]].btn))
        else:
            self.go.setText(tr("{n}개 도구 적용", n=len(ids)))

    def tool(self) -> tools.Tool:
        return self.tools[self.cur]

    def _merge_trim(self) -> bool:
        """합치기와 자르기를 함께 쓰면 자르기 시간은 합친 결과를 기준으로 한다."""
        return self._is_checked(MERGE_TOOLS) and self._is_checked(TRIM_TOOLS)

    def _preview_duration(self) -> float:
        return float(self.items[self._pi]["info"].duration or 0.0) if self.items else 0.0

    def _refresh_range_source(self) -> None:
        if not self.items:
            return
        merged = self._merge_trim()
        if merged:
            self.range.set_duration(sum((it["info"].duration or 0.0) for it in self.items))
            self.range.set_peaks([])
        else:
            self.range.set_duration(self._preview_duration())
            self.range.set_peaks(self._peaks)
        self._on_time_typed()
        self.range.set_playhead(None if merged else (self.player.position_seconds() if self.player else None))

    def _update_side(self) -> None:
        """도구에 따라 미리보기 쪽 표시를 바꾼다 (구간 막대, 크롭 상자, 파형, 재생 막대)."""
        if not self.tools:
            return
        tid = self.tool().id
        audio = self.module == "audio"
        trim = tid in TRIM_TOOLS
        merged = self._merge_trim()
        self.view.setVisible(not audio)
        self.range.setMinimumHeight(76 if audio else 28)
        self.range.setVisible(audio or trim)
        self.times.setVisible(audio or trim)
        self.range.set_interactive(trim)
        self.controls.setVisible(self.player is not None and self.module in ("video", "audio"))
        self.mark_row.setVisible(trim and self.player is not None and not merged)
        self.note.setText(tr("합치기와 함께 쓰면 자르기 시간은 합친 결과 기준이에요.") if merged else "")
        self._update_crop()
        self._update_times()

    def _update_crop(self) -> None:
        if not self.tools or self.tool().id not in CROP_TOOLS:
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
    def _trim_panel(self) -> OptionPanel | None:
        for i, t in enumerate(self.tools):
            if t.id in TRIM_TOOLS:
                return self.panels[i]
        return None

    def _on_range_dragged(self, start: float, end: float) -> None:
        dur = self.range._dur
        s = "" if start < 0.05 else fmt_time(start)
        e = "" if dur - end < 0.05 else fmt_time(end)
        for p in self.panels:
            p.set_time(s, e)
        self._update_times()

    def _on_time_typed(self) -> None:
        panel = self._trim_panel()
        if panel is None:
            return
        vals = panel.values()
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

    def _mark(self, is_start: bool) -> None:
        """지금 재생 위치를 자르기의 시작/끝으로 정한다."""
        if self.player is None or self._merge_trim() or not self.range._dur:
            return
        pos = self.player.position_seconds()
        s, e = self.range.range_seconds()
        if is_start:
            s = pos
        else:
            e = pos
        if e - s < 0.1:
            return
        self.range.set_range(s, e)
        self._on_range_dragged(*self.range.range_seconds())

    # ================================================================ 재생
    def _clip(self) -> tuple[float, float] | None:
        """자르기를 체크했으면 그 구간만 재생한다."""
        if self._is_checked(TRIM_TOOLS) and not self._merge_trim() and self.range._dur:
            s, e = self.range.range_seconds()
            if e - s > 0.1:
                return s, e
        return None

    def _toggle_play(self) -> None:
        pl = self.player
        if pl is None:
            return
        if not pl.is_playing():
            pos, dur = pl.position_seconds(), self._preview_duration()
            clip = self._clip()
            if clip and (pos < clip[0] - 0.05 or pos >= clip[1] - 0.05):
                pl.seek(clip[0])
            elif dur and pos >= dur - 0.1:
                pl.seek(0)
        pl.toggle()

    def _on_seeked(self, frac: float) -> None:
        if self.player is not None:
            self.player.seek(frac * self._preview_duration())

    def _on_position(self, sec: float) -> None:
        dur = self._preview_duration()
        if dur and not self.seek.isSliderDown():
            self.seek.blockSignals(True)
            self.seek.setValue(int(min(sec / dur, 1.0) * 1000))
            self.seek.blockSignals(False)
        self.pos_lbl.setText(f"{fmt_time(sec)} / {fmt_time(dur)}")
        self.range.set_playhead(None if self._merge_trim() else sec)
        clip = self._clip()
        if clip and self.player.is_playing() and sec >= clip[1]:
            self.player.pause()

    def _on_playing(self, on: bool) -> None:
        self.play_btn.setIcon(icons.icon("pause" if on else "play"))
        if on and self.module == "video":
            self.view.setCurrentIndex(1)

    def _on_stopped(self) -> None:
        if self.module == "video":
            self.view.setCurrentIndex(0)

    def _on_play_failed(self, msg: str) -> None:
        self.play_btn.setEnabled(False)
        self.play_err.setText(tr("이 파일은 미리 재생할 수 없어요. 편집은 그대로 할 수 있어요."))

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
            self._peaks = list(peaks)
            if not self._merge_trim():
                self.range.set_peaks(self._peaks)

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
        if self.player is not None and self.items and not self.player.loaded and self.module in ("video", "audio"):
            self.player.load(self.items[self._pi]["path"])      # 작업을 마치고 돌아왔을 때
            self.play_btn.setEnabled(True)
        super().showEvent(e)

    def hideEvent(self, e) -> None:
        if self.player is not None and not e.spontaneous():     # 창을 최소화한 것은 제외
            self.player.unload()                                # 작업 중에는 원본 파일을 붙잡지 않는다
        super().hideEvent(e)

    def _run(self) -> None:
        ids = self._checked_idx()
        steps = [(self.tools[i], self.panels[i].values()) for i in ids]
        items = self.items
        for i in ids:
            if self.tools[i].multi:               # 합치기: 목록에 보이는 순서대로
                by_path = {it["path"]: it for it in self.items}
                items = [by_path[p] for p in self.panels[i].file_order() if p in by_path]
        self.run_requested.emit(steps, items, self.out_ext)
