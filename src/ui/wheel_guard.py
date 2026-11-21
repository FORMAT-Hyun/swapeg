"""마우스 휠을 굴리다가 드롭다운/숫자 칸의 값이 실수로 바뀌지 않게 막는다."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QSlider


class WheelGuard(QObject):
    """QApplication 에 설치하면 모든 콤보박스/스핀박스/슬라이더의 휠 입력을 무시한다."""

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Wheel and isinstance(obj, (QComboBox, QAbstractSpinBox, QSlider)):
            event.ignore()
            return True
        return False
