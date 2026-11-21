import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core import i18n  # noqa: E402
from core.ffpath import app_dir  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_theme  # noqa: E402
from ui.wheel_guard import WheelGuard  # noqa: E402


def main() -> int:
    if sys.platform == "win32":  # 작업 표시줄에 python 이 아니라 Swapeg 아이콘이 보이게
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Swapeg.App")
        except Exception:
            pass
    app = QApplication(sys.argv)
    guard = WheelGuard(app)            # 휠로 드롭다운 값이 바뀌는 것을 막는다
    app.installEventFilter(guard)
    i18n.set_language(i18n.resolve(str(QSettings("Swapeg", "Swapeg").value("language", "auto"))))
    icon = app_dir() / "assets" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    apply_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
