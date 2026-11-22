"""코드로 그리는 선 아이콘 (이미지 파일 없이 색을 바꿔 쓸 수 있다)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

GREEN = "#2e9e5b"
MINT_DARK = "#0b3d33"
MUTED = "#6b7f77"


def _path(*pts: tuple[float, float], close: bool = False) -> QPainterPath:
    p = QPainterPath()
    p.moveTo(QPointF(*pts[0]))
    for pt in pts[1:]:
        p.lineTo(QPointF(*pt))
    if close:
        p.closeSubpath()
    return p


def _draw(name: str, p: QPainter) -> None:
    """24x24 좌표계에 그린다."""
    if name == "gear":
        p.drawEllipse(QPointF(12, 12), 3.2, 3.2)
        p.drawEllipse(QPointF(12, 12), 7.2, 7.2)
        for k in range(8):
            a = math.radians(k * 45)
            p.drawLine(QPointF(12 + 7.2 * math.cos(a), 12 + 7.2 * math.sin(a)),
                       QPointF(12 + 10 * math.cos(a), 12 + 10 * math.sin(a)))
    elif name == "info":
        p.drawEllipse(QPointF(12, 12), 9, 9)
        p.drawLine(QPointF(12, 11), QPointF(12, 16.5))
        p.drawLine(QPointF(12, 7.6), QPointF(12, 7.7))
    elif name == "back":
        p.drawPath(_path((15, 5), (8, 12), (15, 19)))
    elif name == "folder":
        p.drawPath(_path((3, 7), (9, 7), (11, 9.5), (21, 9.5), (21, 19), (3, 19), close=True))
    elif name == "plus":
        p.drawLine(QPointF(12, 5), QPointF(12, 19))
        p.drawLine(QPointF(5, 12), QPointF(19, 12))
    elif name == "close":
        p.drawLine(QPointF(6, 6), QPointF(18, 18))
        p.drawLine(QPointF(18, 6), QPointF(6, 18))
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6, 6)
        p.drawLine(QPointF(15, 15), QPointF(20, 20))
    elif name == "video":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2.5, 2.5)
        p.drawPath(_path((10, 9), (10, 15), (15, 12), close=True))
    elif name == "audio":
        p.drawPath(_path((9, 17), (9, 6), (19, 4), (19, 15)))
        p.drawEllipse(QPointF(7, 17), 2.4, 2.4)
        p.drawEllipse(QPointF(17, 15), 2.4, 2.4)
    elif name == "image":
        p.drawRoundedRect(QRectF(3, 4, 18, 16), 2.5, 2.5)
        p.drawEllipse(QPointF(8.5, 9.5), 1.7, 1.7)
        p.drawPath(_path((3.5, 17), (9, 12), (14, 17), (17, 14), (20.5, 17.5)))
    elif name == "swap":
        p.drawPath(_path((4, 8), (20, 8)))
        p.drawPath(_path((16, 4), (20, 8), (16, 12)))
        p.drawPath(_path((20, 16), (4, 16)))
        p.drawPath(_path((8, 12), (4, 16), (8, 20)))
    elif name == "upload":
        p.drawLine(QPointF(12, 16), QPointF(12, 4))
        p.drawPath(_path((7, 9), (12, 4), (17, 9)))
        p.drawPath(_path((4, 15), (4, 20), (20, 20), (20, 15)))
    elif name == "check":
        p.drawPath(_path((5, 12.5), (10, 17.5), (19, 7)))
    elif name == "scissors":
        p.drawEllipse(QPointF(6, 6.5), 2.6, 2.6)
        p.drawEllipse(QPointF(6, 17.5), 2.6, 2.6)
        p.drawLine(QPointF(8.2, 8), QPointF(20, 17.5))
        p.drawLine(QPointF(8.2, 16), QPointF(20, 6.5))
    elif name == "stack":
        p.drawPath(_path((12, 4), (21, 9), (12, 14), (3, 9), close=True))
        p.drawPath(_path((3, 13), (12, 18), (21, 13)))
        p.drawPath(_path((3, 17), (12, 22), (21, 17)))
    elif name == "aspect":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2.5, 2.5)
        p.drawRoundedRect(QRectF(7.5, 9, 6, 6), 1.2, 1.2)
    elif name == "gauge":
        p.drawArc(QRectF(3, 6, 18, 18), 0, 180 * 16)
        p.drawLine(QPointF(12, 15), QPointF(16.5, 10))
        p.drawLine(QPointF(3, 15), QPointF(21, 15))
    elif name == "volume":
        p.drawPath(_path((4, 10), (8, 10), (13, 6), (13, 18), (8, 14), (4, 14), close=True))
        p.drawArc(QRectF(11, 8, 8, 8), -60 * 16, 120 * 16)
    elif name == "subtitles":
        p.drawRoundedRect(QRectF(3, 5, 18, 14), 2.5, 2.5)
        p.drawLine(QPointF(7, 11), QPointF(11, 11))
        p.drawLine(QPointF(13, 11), QPointF(17, 11))
        p.drawLine(QPointF(7, 15), QPointF(14, 15))
    elif name == "crop":
        p.drawPath(_path((6, 2), (6, 18), (22, 18)))
        p.drawPath(_path((2, 6), (18, 6), (18, 22)))
    elif name == "drop":
        p.drawEllipse(QPointF(12, 15), 6, 6)
        p.drawLine(QPointF(12, 3), QPointF(7.4, 11))
        p.drawLine(QPointF(12, 3), QPointF(16.6, 11))
    elif name in ("reset", "rotate"):
        p.drawArc(QRectF(5, 5, 14, 14), 40 * 16, 280 * 16)
        p.drawPath(_path((17.5, 3.5), (17.5, 8), (13, 8)))


def pixmap(name: str, color: str = GREEN, size: int = 64, width: float = 1.9) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    p.setPen(QPen(QColor(color), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    _draw(name, p)
    p.end()
    return pm


def icon(name: str, color: str = GREEN) -> QIcon:
    return QIcon(pixmap(name, color, 96))
