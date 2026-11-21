import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core import simple  # noqa: E402
from ui.format_grid import FormatGrid  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_defaults_per_kind(app):
    g = FormatGrid()
    g.rebuild(lambda e, k: k == "video")
    assert g.current() == "mp4"
    g.rebuild(lambda e, k: k == "image")
    assert g.current() == "png"
    g.rebuild(lambda e, k: k == "audio")
    assert g.current() == "mp3"


def test_search_filters_and_enter_picks_first(app):
    g = FormatGrid()
    g.rebuild(lambda e, k: True)
    g.filter("mp")
    sec_chips = {e: b for s in g._sections for e, b in s.chips.items()}
    assert not sec_chips["mp4"].isHidden() and not sec_chips["mp3"].isHidden()
    assert sec_chips["png"].isHidden()
    g.filter("이미지")
    assert not sec_chips["png"].isHidden() and sec_chips["mp4"].isHidden()
    g.filter("jpg")
    assert g.first_visible() == "jpg"
    g.select("jpg")
    assert g.current() == "jpg"
    g.filter("")
    assert not sec_chips["mp4"].isHidden()


def test_selection_kept_when_still_allowed(app):
    g = FormatGrid()
    g.rebuild(lambda e, k: True)
    g.select("flac")
    g.rebuild(lambda e, k: k in ("video", "audio"))
    assert g.current() == "flac"

