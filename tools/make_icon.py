"""Swapeg 아이콘 생성: 민트색 둥근 사각형 위에 서로 바꾸는 화살표(⇄).

실행: .venv\\Scripts\\python tools\\make_icon.py  ->  assets/icon.png, assets/icon.ico
"""
from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QGuiApplication, QImage, QLinearGradient, QPainter,  # noqa: E402
                           QPainterPath, QPen)

ROOT = Path(__file__).resolve().parents[1]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw(size: int) -> QImage:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = float(size)

    # 배경: 민트 그라데이션 둥근 사각형
    rect = QRectF(s * 0.04, s * 0.04, s * 0.92, s * 0.92)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, QColor("#5fe0c0"))
    g.setColorAt(1, QColor("#22a888"))
    p.setPen(Qt.NoPen)
    p.setBrush(g)
    p.drawRoundedRect(rect, s * 0.22, s * 0.22)

    # 화살표 두 개 (위: 오른쪽, 아래: 왼쪽) — 서로 바꾼다(swap)는 뜻
    pen = QPen(QColor("white"), s * 0.085, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    def arrow(y: float, x0: float, x1: float) -> None:
        d = s * 0.11 if x1 > x0 else -s * 0.11
        path = QPainterPath()
        path.moveTo(QPointF(x0, y))
        path.lineTo(QPointF(x1, y))
        path.moveTo(QPointF(x1 - d, y - s * 0.11))
        path.lineTo(QPointF(x1, y))
        path.lineTo(QPointF(x1 - d, y + s * 0.11))
        p.drawPath(path)

    arrow(s * 0.37, s * 0.25, s * 0.75)
    arrow(s * 0.63, s * 0.75, s * 0.25)
    p.end()
    return img


def png_bytes(img: QImage) -> bytes:
    ba = QByteArray()
    buf = QBuffer(ba)
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return bytes(ba)


def write_ico(path: Path, sizes: list[int]) -> None:
    """PNG를 그대로 담는 ICO (Windows Vista 이후 지원)."""
    images = [(n, png_bytes(draw(n))) for n in sizes]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, blobs = b"", b""
    for n, data in images:
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        blobs += data
        offset += len(data)
    path.write_bytes(header + entries + blobs)


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    draw(512).save(str(out / "icon.png"))
    write_ico(out / "icon.ico", ICO_SIZES)
    print("만들었습니다:", out / "icon.png", out / "icon.ico")
    return 0


if __name__ == "__main__":
    sys.exit(main())
