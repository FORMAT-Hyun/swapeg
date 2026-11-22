"""앱 전체 흐름(시작 화면 -> 모듈 -> 도구 -> 진행/결과)을 화면 없이 실제 ffmpeg로 돌려 본다."""
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.ffpath import find_tool  # noqa: E402

FF = find_tool("ffmpeg")
pytestmark = pytest.mark.skipif(not FF, reason="ffmpeg 없음")


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def win(app, tmp_path, monkeypatch):
    from ui import main_window
    from ui.main_window import MainWindow
    # 실제 사용자 설정을 건드리지 않도록 임시 ini 파일을 쓴다
    monkeypatch.setattr(main_window, "QSettings", lambda *a: QSettings(str(tmp_path / "s.ini"), QSettings.IniFormat))
    w = MainWindow()
    w.show()
    yield w
    w.close()


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    d = tmp_path_factory.mktemp("흐름 샘플")
    v, a, i = d / "영상.mp4", d / "음악.mp3", d / "그림.png"
    subprocess.run([FF, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=4", "-f", "lavfi",
                    "-i", "sine=duration=4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(v)],
                   check=True, capture_output=True)
    subprocess.run([FF, "-y", "-f", "lavfi", "-i", "sine=duration=5", str(a)], check=True, capture_output=True)
    subprocess.run([FF, "-y", "-f", "lavfi", "-i", "testsrc=size=120x80", "-frames:v", "1", str(i)],
                   check=True, capture_output=True)
    return {"v": v, "a": a, "i": i}


def wait_done(app, w, timeout=60):
    t = time.time()
    while time.time() - t < timeout:
        app.processEvents()
        if not w.runner.running and w.btn_again.isVisible():
            return
        time.sleep(0.02)
    raise AssertionError("작업이 끝나지 않았습니다")


def test_home_routes_dropped_files(app, win, files):
    from ui.main_window import PAGE_HOME, PAGE_PICK, PAGE_TOOL
    assert win.stack.currentIndex() == PAGE_HOME
    win._add_files([str(files["v"])])
    assert win.stack.currentIndex() == PAGE_TOOL and win._module == "video"
    win._reset()
    win._add_files([str(files["a"])])
    assert win._module == "audio" and win.stack.currentIndex() == PAGE_TOOL
    win._reset()
    win._add_files([str(files["i"])])
    assert win._module == "photo"
    win._reset()
    win._add_files([str(files["v"]), str(files["i"])])      # 종류가 섞이면 형식 변환으로
    assert win.stack.currentIndex() == PAGE_PICK


def test_module_rejects_wrong_kind(app, win, files):
    from ui.main_window import PAGE_MDROP
    win._open_module("video")
    win._add_files([str(files["i"])])
    assert win.stack.currentIndex() == PAGE_MDROP and not win.items and win.mdrop_guide.text()


def test_trim_through_the_ui(app, win, files):
    from ui.main_window import PAGE_RUN, PAGE_TOOL
    win._open_module("video")
    win._add_files([str(files["v"])])
    tp = win.tool_page
    panel = tp.panels[0]
    panel._edits["start"].setText("1")
    panel._edits["end"].setText("3")
    tp._on_time_typed()
    assert tp.range.range_seconds()[0] == pytest.approx(1, abs=0.1)
    tp._run()
    assert win.stack.currentIndex() == PAGE_RUN
    wait_done(app, win)
    assert win.run_title.text() and win._ok_outs and Path(win._ok_outs[0]).exists()
    assert win.btn_edit.isVisible()                       # 같은 파일로 계속 편집
    win.btn_edit.click()
    assert win.stack.currentIndex() == PAGE_TOOL


def test_range_bar_drag_fills_time_fields(app, win, files):
    win._open_module("audio")
    win._add_files([str(files["a"])])
    tp = win.tool_page
    tp.range._drag = "a"
    tp.range._move(0.4)                                    # 앞 손잡이를 40% 지점으로
    tp.range._drag = None
    assert tp.panels[0].values()["start"] not in ("", "0:00.0")


def test_tool_error_shows_message_not_crash(app, win, files, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    win._open_module("video")
    win._add_files([str(files["v"])])
    win.tool_page._run()                                   # 아무 값도 안 넣고 실행
    assert shown and not win.runner.running


def test_converter_still_works(app, win, files):
    win._open_module("convert")
    win._add_files([str(files["i"])])
    assert win.grid.current()
    win.grid.select("jpg")
    win._start()
    wait_done(app, win)
    assert win._ok_outs and Path(win._ok_outs[0]).suffix == ".jpg"


def test_merge_uses_list_order(app, win, files):
    win._open_module("audio")
    win._add_files([str(files["a"])])
    win._add_files([str(files["a"])])                       # 같은 파일은 무시된다
    assert len(win.items) == 1
    tp = win.tool_page
    tp._select_tool(1)
    from core.probe import probe
    extra = {"path": str(files["v"]), "info": probe(find_tool("ffprobe"), str(files["v"])), "kind": "video"}
    win.items.append(extra)
    tp.set_items(win.items)
    tp.panels[1]._list.insertItem(0, tp.panels[1]._list.takeItem(1))   # 순서 바꾸기
    assert tp.panels[1].file_order()[0] == str(files["v"])
    tp._run()
    wait_done(app, win)
    assert win._ok_outs
