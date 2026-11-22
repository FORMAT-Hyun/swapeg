"""구간 막대: 두 손잡이를 끌어 시작/끝을 정한다. 오디오는 파형을 배경에 그린다."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

MINT = QColor("#2fc9a5")
GREEN = QColor("#2e9e5b")


class RangeBar(QWidget):
    rangeChanged = Signal(float, float)      # 사용자가 끌어서 바꿨을 때 (시작초, 끝초)

    def __init__(self, tall: bool = False, parent=None):
        super().__init__(parent)
        self._dur = 0.0
        self._a, self._b = 0.0, 1.0           # 0~1 비율
        self._peaks: list[float] = []
        self._interactive = True
        self._drag: str | None = None
        self.setMinimumHeight(76 if tall else 28)
        self.setMouseTracking(True)

    # ------------------------------------------------------------ 값
    def set_duration(self, d: float | None) -> None:
        self._dur = float(d or 0.0)
        self.update()

    def set_peaks(self, peaks: list[float]) -> None:
        self._peaks = list(peaks or [])
        self.update()

    def set_interactive(self, on: bool) -> None:
        self._interactive = on
        self.update()

    def set_range(self, start: float | None, end: float | None) -> None:
        """초 단위로 구간을 지정 (None 이면 처음/끝). 잘못된 값은 무시."""
        if self._dur <= 0:
            return
        a = 0.0 if start is None else max(0.0, min(start / self._dur, 1.0))
        b = 1.0 if end is None else max(0.0, min(end / self._dur, 1.0))
        if b - a < 0.002:
            return
        self._a, self._b = a, b
        self.update()

    def range_seconds(self) -> tuple[float, float]:
        return self._a * self._dur, self._b * self._dur

    # ------------------------------------------------------------ 그리기
    def _track(self) -> QRectF:
        return QRectF(8, 4, max(self.width() - 16, 1), self.height() - 8)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = self._track()
        base = QColor(128, 140, 136, 60)
        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawRoundedRect(t, 6, 6)
        x1, x2 = t.left() + self._a * t.width(), t.left() + self._b * t.width()
        if self._peaks:                                    # 파형 막대
            n = len(self._peaks)
            bw = t.width() / n
            mid = t.center().y()
            for i, v in enumerate(self._peaks):
                x = t.left() + i * bw
                inside = x1 - bw <= x <= x2
                h = max(2.0, v * (t.height() - 6))
                p.setBrush(MINT if inside and self._interactive else (QColor(128, 140, 136, 150)
                                                                      if not inside else MINT))
                p.drawRoundedRect(QRectF(x + 0.5, mid - h / 2, max(bw - 1.5, 1), h), 1.5, 1.5)
        else:                                              # 선택 구간만 칠한다
            p.setBrush(MINT)
            p.drawRoundedRect(QRectF(x1, t.top() + t.height() / 2 - 4, max(x2 - x1, 1), 8), 4, 4)
        if self._interactive:
            for x in (x1, x2):
                p.setBrush(GREEN)
                p.drawRoundedRect(QRectF(x - 4, t.top(), 8, t.height()), 3, 3)
        p.end()

    # ------------------------------------------------------------ 끌기
    def _frac(self, x: float) -> float:
        t = self._track()
        return max(0.0, min((x - t.left()) / t.width(), 1.0))

    def mousePressEvent(self, e) -> None:
        if not self._interactive or self._dur <= 0 or e.button() != Qt.LeftButton:
            return
        f = self._frac(e.position().x())
        self._drag = "a" if abs(f - self._a) <= abs(f - self._b) else "b"
        self._move(f)

    def mouseMoveEvent(self, e) -> None:
        if self._drag:
            self._move(self._frac(e.position().x()))
        elif self._interactive:
            self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag = None

    def _move(self, f: float) -> None:
        gap = 0.01
        if self._drag == "a":
            self._a = max(0.0, min(f, self._b - gap))
        else:
            self._b = min(1.0, max(f, self._a + gap))
        self.update()
        s, e = self.range_seconds()
        self.rangeChanged.emit(s, e)
