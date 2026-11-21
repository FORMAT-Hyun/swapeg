import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402
from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QComboBox, QSpinBox  # noqa: E402

from ui.wheel_guard import WheelGuard  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _wheel(widget, delta=-120):
    ev = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, delta), Qt.NoButton,
                     Qt.NoModifier, Qt.NoScrollPhase, False)
    QApplication.sendEvent(widget, ev)


def test_wheel_changes_combo_without_guard(app):
    c = QComboBox()
    c.addItems(["a", "b", "c"])
    c.show()
    _wheel(c)
    assert c.currentIndex() == 1            # 가드가 없으면 휠로 값이 바뀐다


def test_wheel_guard_blocks_combo_and_spin(app):
    guard = WheelGuard(app)
    app.installEventFilter(guard)
    try:
        c = QComboBox()
        c.addItems(["a", "b", "c"])
        c.show()
        s = QSpinBox()
        s.setRange(0, 10)
        s.show()
        _wheel(c)
        _wheel(s, 120)
        assert c.currentIndex() == 0 and s.value() == 0
    finally:
        app.removeEventFilter(guard)
