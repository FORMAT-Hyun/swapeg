import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.main_window import MainWindow  # noqa: E402
from ui.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
