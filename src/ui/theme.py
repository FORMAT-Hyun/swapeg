"""밝은 테마: 기본색 민트, 배경 흰색, 보조색 초록."""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QWidget

from core.ffpath import app_dir

# --- 색 ----------------------------------------------------------------
ACCENT = "#2fc9a5"          # 기본색: 민트
ACCENT_HOVER = "#4ad6b5"
ACCENT_PRESS = "#23ad8d"
ACCENT_SOFT = "#dff7ef"     # 선택/강조 배경
ON_ACCENT = "#0b3d33"       # 민트 버튼 위 글자(대비 확보용 진한 초록)
GREEN = "#2e9e5b"           # 보조색: 초록
GREEN_SOFT = "#e6f5ec"
BG = "#ffffff"              # 배경: 흰색
SURFACE = "#f6faf8"
SURFACE2 = "#eaf3ef"
INPUT_BG = "#ffffff"
BORDER = "#dbe7e2"
BORDER_STRONG = "#c3d6ce"
TEXT = "#1c2b26"
MUTED = "#6b7f77"
PLACEHOLDER = "#9ab0a8"
DISABLED = "#a9b8b2"
ROW_HOVER = "#eef7f3"

FONT_STACK = '"Pretendard", "Segoe UI", "Malgun Gothic", "Noto Sans KR", sans-serif'


def _qss() -> str:
    assets = app_dir() / "assets"
    chevron = (assets / "chevron_down.svg").as_posix()
    return f"""
* {{ font-family: {FONT_STACK}; font-size: 10pt; color: {TEXT}; }}
QMainWindow, QDialog {{ background: {BG}; }}
QLabel {{ background: transparent; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Title {{ font-size: 18pt; font-weight: 700; color: {GREEN}; }}
QFrame#Preview {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#PreviewImg {{ background: {SURFACE2}; border-radius: 8px; color: {MUTED}; font-size: 11pt; }}
QLabel#PreviewName {{ font-weight: 600; }}
QLabel#SectionLabel {{ color: {GREEN}; font-weight: 600; font-size: 10pt; }}
QLabel#Error {{ color: #d64545; }}
QLabel#BigTitle {{ font-size: 20pt; font-weight: 700; color: {GREEN}; }}
QLabel#BigPct {{ font-size: 34pt; font-weight: 700; color: {TEXT}; }}
QProgressBar#BigBar {{ background: {SURFACE2}; border-radius: 8px; min-height: 16px; max-height: 16px; }}
QProgressBar#BigBar::chunk {{ background: {ACCENT}; border-radius: 8px; }}
QPushButton[fmt="true"] {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; border-radius: 12px;
    padding: 12px 8px; min-width: 88px; font-size: 11pt; font-weight: 600;
}}
QPushButton[fmt="true"]:hover {{ background: {GREEN_SOFT}; border-color: {GREEN}; }}
QPushButton[fmt="true"]:checked {{
    background: {ACCENT}; border-color: {ACCENT}; color: {ON_ACCENT}; font-weight: 700;
}}
QScrollArea {{ background: transparent; border: none; }}
QWidget#GridInner {{ background: transparent; }}
QLabel#DropHint {{ color: {MUTED}; font-size: 10pt; }}
QDialog QGroupBox {{ margin-top: 14px; }}
QRadioButton, QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QLabel#DropGuide {{ color: {MUTED}; font-size: 13pt; }}
QPushButton#DropZone:hover QLabel#DropGuide {{ color: {GREEN}; }}
QPushButton#DropZone {{
    background: {SURFACE}; border: 2px dashed {BORDER_STRONG}; border-radius: 16px;
    color: {MUTED}; font-size: 13pt; padding: 40px;
}}
QPushButton#DropZone:hover {{ border-color: {ACCENT}; background: {ACCENT_SOFT}; color: {GREEN}; }}

/* 카드 */
QGroupBox {{
    border: 1px solid {BORDER}; border-radius: 12px; margin-top: 16px;
    padding: 16px 12px 10px 12px; background: {SURFACE};
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {GREEN}; font-weight: 600;
}}

/* 입력 */
QLineEdit, QComboBox, QSpinBox {{
    background: {INPUT_BG}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; padding: 6px 10px;
}}
QLineEdit, QSpinBox {{ selection-background-color: {ACCENT}; selection-color: {ON_ACCENT}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{ color: {DISABLED}; background: {SURFACE}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{chevron}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; outline: none; padding: 4px;
    selection-background-color: {ACCENT_SOFT}; selection-color: {TEXT};
}}
QComboBox QAbstractItemView::item {{ padding: 6px 10px; min-height: 22px; border-radius: 4px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}

/* 버튼 */
QPushButton {{
    background: {BG}; border: 1px solid {BORDER_STRONG}; border-radius: 8px; padding: 6px 14px;
}}
QPushButton:hover {{ background: {GREEN_SOFT}; border-color: {GREEN}; }}
QPushButton:pressed {{ background: {SURFACE2}; }}
QPushButton:disabled {{ color: {DISABLED}; background: {SURFACE}; border-color: {BORDER}; }}
QPushButton[primary="true"] {{
    background: {ACCENT}; border: 1px solid {ACCENT}; color: {ON_ACCENT}; font-weight: 700; padding: 8px 20px;
}}
QPushButton[primary="true"]:hover {{ background: {ACCENT_HOVER}; border-color: {ACCENT_HOVER}; }}
QPushButton[primary="true"]:pressed {{ background: {ACCENT_PRESS}; border-color: {ACCENT_PRESS}; }}
QPushButton[primary="true"]:disabled {{ background: #c4ebe0; border-color: #c4ebe0; color: #7fa89c; }}
QPushButton[ghost="true"] {{
    background: transparent; border: none; color: {GREEN}; padding: 6px 10px;
}}
QPushButton[ghost="true"]:hover {{ background: {GREEN_SOFT}; color: {GREEN}; }}
QPushButton[ghost="true"]:disabled {{ color: {DISABLED}; background: transparent; }}

/* 진행 막대 */
QProgressBar {{ background: {SURFACE2}; border: none; border-radius: 2px; max-height: 4px; min-height: 4px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}

/* 표 */
QTableWidget {{
    background: {BG}; border: 1px solid {BORDER}; border-radius: 10px; outline: none;
    alternate-background-color: {SURFACE};
}}
QTableWidget::item {{ padding: 5px 6px; border: none; }}
QTableWidget::item:selected {{ background: {ACCENT_SOFT}; color: {TEXT}; }}
QTableWidget::item:hover {{ background: {ROW_HOVER}; }}
QHeaderView::section {{
    background: {BG}; color: {GREEN}; font-weight: 600; border: none;
    border-bottom: 1px solid {BORDER}; padding: 6px 8px;
}}
QTableCornerButton::section {{ background: {BG}; border: none; }}

/* 스크롤 */
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #c9dcd4; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #a9c7bb; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; width: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QSplitter::handle {{ background: transparent; }}

QPlainTextEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    font-family: "Cascadia Mono", Consolas, "D2Coding", monospace; font-size: 9pt;
}}
QToolTip {{
    background: {BG}; color: {TEXT}; border: 1px solid {BORDER_STRONG}; padding: 6px 8px; border-radius: 6px;
}}
QProgressDialog, QMessageBox {{ background: {BG}; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    C = QPalette.ColorRole
    for role, color in ((C.Window, BG), (C.WindowText, TEXT), (C.Base, INPUT_BG),
                        (C.AlternateBase, SURFACE), (C.Text, TEXT), (C.Button, BG),
                        (C.ButtonText, TEXT), (C.Highlight, ACCENT), (C.HighlightedText, ON_ACCENT),
                        (C.ToolTipBase, BG), (C.ToolTipText, TEXT),
                        (C.PlaceholderText, PLACEHOLDER), (C.Link, GREEN)):
        pal.setColor(role, QColor(color))
    for role in (C.Text, C.ButtonText, C.WindowText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, QColor(DISABLED))
    app.setPalette(pal)
    app.setStyleSheet(_qss())


def repolish(w: QWidget) -> None:
    w.style().unpolish(w)
    w.style().polish(w)
    w.update()
