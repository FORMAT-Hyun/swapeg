import ast
import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from core import i18n, simple  # noqa: E402
from core.i18n import EN, tr  # noqa: E402


def _tr_keys():
    """소스 안의 tr("...") 첫 인자 문자열을 전부 모은다."""
    keys = {}
    for py in SRC.rglob("*.py"):
        if py.name == "i18n.py":
            continue
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "tr" and node.args
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                keys[node.args[0].value] = py.name
    return keys


def test_every_tr_string_has_english():
    missing = {k: f for k, f in _tr_keys().items() if k not in EN}
    assert not missing, missing


def test_dynamic_titles_have_english():
    for t in simple.KIND_TITLE.values():
        assert t in EN
    for _key, title, desc in simple.QUALITY_LEVELS:
        assert title in EN and desc in EN


def test_tool_specs_have_english():
    from core import tools
    texts = set()
    for name, _icon in tools.MODULES.values():
        texts.add(name)
    for ts in tools.TOOLS.values():
        for t in ts:
            texts.update([t.name, t.btn])
            for f in t.fields:
                texts.update(x for x in (f.label, f.pick_title, f.pick_filter, f.unit) if x and not f.unit == x)
                texts.update(label for _v, label in f.options)
    missing = sorted(x for x in texts if x not in EN and not re.fullmatch(r"[\d.%°:x ]+|\d+p|\d+", x))
    assert not missing, missing


def test_placeholders_match():
    for ko, en in EN.items():
        assert sorted(re.findall(r"\{\w+(?::[^}]*)?\}", ko)) == sorted(re.findall(r"\{\w+(?::[^}]*)?\}", en)), ko


def test_english_has_no_korean():
    for ko, en in EN.items():
        assert not re.search(r"[가-힣]", en), (ko, en)


def test_tr_and_resolve():
    try:
        i18n.set_language("en")
        assert tr("파일 추가") == "Add files"
        assert tr("{n}개 변환 완료", n=3) == "3 converted"
        i18n.set_language("ko")
        assert tr("파일 추가") == "파일 추가"
        assert tr("{n}개 변환 완료", n=3) == "3개 변환 완료"
        assert i18n.resolve("en") == "en" and i18n.resolve("ko") == "ko"
        assert i18n.resolve("auto") in ("ko", "en")
    finally:
        i18n.set_language("ko")


def _all_texts(root):
    """위젯 트리에서 사용자에게 보이는 글자를 전부 모은다."""
    from PySide6.QtWidgets import QAbstractButton, QLabel, QLineEdit
    out = []
    for w in [root, *root.findChildren(object)]:
        if isinstance(w, (QLabel, QAbstractButton)):
            out.append(w.text())
        if isinstance(w, QLineEdit):
            out.append(w.placeholderText())
        if hasattr(w, "toolTip"):
            out.append(w.toolTip())
        if hasattr(w, "windowTitle"):
            out.append(w.windowTitle())
    return [t for t in out if t]


def test_english_ui_shows_no_korean_anywhere():
    """영어로 바꾸고 모든 모듈/도구/대화상자를 열어, 한글이 남은 글자가 없는지 본다."""
    from PySide6.QtWidgets import QApplication
    from core import tools
    from core.probe import MediaInfo
    from core.thumb import Thumbs
    from ui.about_dialog import AboutDialog
    from ui.tool_page import ToolPage

    app = QApplication.instance() or QApplication([])
    i18n.set_language("en")
    try:
        bad = []
        thumbs = Thumbs(lambda: None)
        page = ToolPage(thumbs)
        items = {
            "video": {"path": "a.mp4", "kind": "video", "info": MediaInfo(duration=10, width=640, height=360, vcodec="h264", acodec="aac")},
            "audio": {"path": "a.mp3", "kind": "audio", "info": MediaInfo(duration=10, acodec="mp3")},
            "photo": {"path": "a.png", "kind": "image", "info": MediaInfo(width=100, height=80, vcodec="png")},
        }
        page.open(list(items.values()))                 # 세 종류를 한꺼번에 넣어 모든 도구 묶음을 연다
        for i in range(len(page.tools)):
            page._select_tool(i)
            bad += [t for t in _all_texts(page) if re.search(r"[가-힣]", t)]
        bad += [t for t in _all_texts(AboutDialog()) if re.search(r"[가-힣]", t)]
        from ui.main_window import MainWindow
        win = MainWindow()                       # 시작(파일 넣기) 화면, 형식 변환, 진행 화면 포함
        bad += [t for t in _all_texts(win) if re.search(r"[가-힣]", t)]
        assert not bad, sorted(set(bad))
    finally:
        i18n.set_language("ko")
