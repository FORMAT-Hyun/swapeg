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
