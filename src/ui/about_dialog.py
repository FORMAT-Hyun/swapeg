"""프로그램 정보 창: 이름/버전, 설명, GitHub 링크, 사용한 소프트웨어."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from core.ffpath import app_dir
from core.i18n import tr
from version import APP_NAME, ISSUES_URL, RELEASES_URL, REPO_URL, __version__


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("프로그램 정보"))
        self.setMinimumWidth(440)
        v = QVBoxLayout(self)
        v.setSpacing(12)

        head = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(app_dir() / "assets" / "icon.png")).scaled(
            64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        titles = QVBoxLayout()
        name = QLabel(APP_NAME)
        name.setObjectName("Title")
        ver = QLabel(f"{tr('버전')} {__version__}")
        ver.setObjectName("Muted")
        titles.addWidget(name)
        titles.addWidget(ver)
        head.addWidget(logo)
        head.addSpacing(12)
        head.addLayout(titles)
        head.addStretch(1)
        v.addLayout(head)

        desc = QLabel(tr("파일을 넣고, 형식을 고르고, 변환만 누르면 끝나는 ffmpeg 변환기입니다. 화질은 원본 그대로 유지합니다."))
        desc.setWordWrap(True)
        v.addWidget(desc)

        links = QLabel(
            f'<a href="{REPO_URL}">{tr("GitHub 저장소")}</a><br>'
            f'<a href="{RELEASES_URL}">{tr("새 버전 확인")}</a><br>'
            f'<a href="{ISSUES_URL}">{tr("문제 신고 / 의견 보내기")}</a>')
        links.setOpenExternalLinks(True)
        links.setTextInteractionFlags(Qt.TextBrowserInteraction)
        links.setStyleSheet("line-height: 160%;")
        v.addWidget(links)

        credits = QLabel(tr("Swapeg는 FFmpeg(gyan.dev의 GPL 빌드)와 Qt for Python(PySide6, LGPL)을 사용합니다. "
                            "FFmpeg 프로젝트와는 관련이 없습니다."))
        credits.setObjectName("Muted")
        credits.setWordWrap(True)
        v.addWidget(credits)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton(tr("닫기"))
        close.setProperty("primary", True)
        close.clicked.connect(self.accept)
        btns.addWidget(close)
        v.addLayout(btns)
