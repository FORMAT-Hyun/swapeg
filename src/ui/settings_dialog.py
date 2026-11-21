"""설정 창: 저장 위치, 화질, 완료 후 동작, 언어, ffmpeg 경로."""
from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QVBoxLayout,
)

from core import simple
from core.i18n import tr
from ui import icons
from version import APP_NAME, __version__


def load(settings: QSettings) -> dict:
    return {
        "out_mode": settings.value("out_mode", "same"),          # same | custom
        "out_dir": settings.value("out_dir", ""),
        "quality": settings.value("quality", "original"),
        "open_after": str(settings.value("open_after", "false")).lower() in ("true", "1"),
        "language": settings.value("language", "auto"),          # auto | ko | en
    }


class SettingsDialog(QDialog):
    def __init__(self, settings: QSettings, ffmpeg_path: str | None, on_pick_ffmpeg, on_reinstall,
                 on_language_changed, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("설정"))
        self.setMinimumWidth(480)
        self._settings = settings
        self._on_language_changed = on_language_changed
        cur = load(settings)

        v = QVBoxLayout(self)
        v.setSpacing(12)

        # 저장 위치
        g1 = QGroupBox(tr("저장 위치"))
        l1 = QVBoxLayout(g1)
        self.r_same = QRadioButton(tr("원본 파일과 같은 폴더"))
        self.r_custom = QRadioButton(tr("지정한 폴더"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(cur["out_dir"])
        self.dir_edit.setPlaceholderText(tr("폴더를 선택하세요"))
        b = QPushButton(tr("찾기"))
        b.setIcon(icons.icon("folder"))
        b.clicked.connect(self._pick_dir)
        row.addWidget(self.dir_edit, 1)
        row.addWidget(b)
        l1.addWidget(self.r_same)
        l1.addWidget(self.r_custom)
        l1.addLayout(row)
        (self.r_custom if cur["out_mode"] == "custom" else self.r_same).setChecked(True)
        self.r_same.toggled.connect(self._sync)
        v.addWidget(g1)

        # 화질
        g2 = QGroupBox(tr("화질"))
        l2 = QVBoxLayout(g2)
        self.q_radios: dict[str, QRadioButton] = {}
        for key, title, desc in simple.QUALITY_LEVELS:
            r = QRadioButton(f"{tr(title)}  -  {tr(desc)}")
            r.setChecked(key == cur["quality"])
            self.q_radios[key] = r
            l2.addWidget(r)
        if not any(r.isChecked() for r in self.q_radios.values()):
            self.q_radios["original"].setChecked(True)
        v.addWidget(g2)

        # 완료 후
        g3 = QGroupBox(tr("변환이 끝나면"))
        l3 = QVBoxLayout(g3)
        self.c_open = QCheckBox(tr("결과 폴더를 자동으로 열기"))
        self.c_open.setChecked(cur["open_after"])
        l3.addWidget(self.c_open)
        v.addWidget(g3)

        # 언어 (바꾸면 앱을 다시 시작해야 적용)
        g5 = QGroupBox(tr("언어"))
        l5 = QVBoxLayout(g5)
        self.lang = QComboBox()
        self.lang.addItem(tr("자동 (시스템 언어)"), "auto")
        self.lang.addItem("한국어", "ko")
        self.lang.addItem("English", "en")
        self.lang.setCurrentIndex(max(0, self.lang.findData(cur["language"])))
        l5.addWidget(self.lang)
        v.addWidget(g5)

        # ffmpeg
        g4 = QGroupBox("ffmpeg")
        l4 = QVBoxLayout(g4)
        path = QLabel(ffmpeg_path or tr("찾을 수 없음"))
        path.setObjectName("Muted")
        path.setWordWrap(True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        r4 = QHBoxLayout()
        b1 = QPushButton(tr("경로 지정"))
        b1.setIcon(icons.icon("folder"))
        b1.clicked.connect(lambda: (self.accept(), on_pick_ffmpeg()))
        b2 = QPushButton(tr("다시 설치"))
        b2.setIcon(icons.icon("reset"))
        b2.clicked.connect(lambda: (self.accept(), on_reinstall()))
        r4.addWidget(b1)
        r4.addWidget(b2)
        r4.addStretch(1)
        l4.addWidget(path)
        l4.addLayout(r4)
        v.addWidget(g4)

        # 버튼
        btns = QHBoxLayout()
        ver = QLabel(f"{APP_NAME} v{__version__}")
        ver.setObjectName("Muted")
        btns.addWidget(ver)
        btns.addStretch(1)
        cancel = QPushButton(tr("취소"))
        cancel.clicked.connect(self.reject)
        ok = QPushButton(tr("저장"))
        ok.setProperty("primary", True)
        ok.setIcon(icons.icon("check", icons.MINT_DARK))
        ok.clicked.connect(self._save)
        btns.addWidget(cancel)
        btns.addWidget(ok)
        v.addLayout(btns)
        self._sync()

    def _sync(self) -> None:
        self.dir_edit.setEnabled(self.r_custom.isChecked())

    def _pick_dir(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("저장할 폴더 선택"), self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)
            self.r_custom.setChecked(True)

    def _save(self) -> None:
        custom = self.r_custom.isChecked() and bool(self.dir_edit.text().strip())
        s = self._settings
        old_lang = str(s.value("language", "auto"))
        s.setValue("out_mode", "custom" if custom else "same")
        s.setValue("out_dir", self.dir_edit.text().strip())
        s.setValue("quality", next(k for k, r in self.q_radios.items() if r.isChecked()))
        s.setValue("open_after", self.c_open.isChecked())
        new_lang = self.lang.currentData()
        s.setValue("language", new_lang)
        self.accept()
        if new_lang != old_lang:
            self._on_language_changed()
