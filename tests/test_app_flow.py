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
    tp._on_chip_clicked(1)                                  # 아직 체크한 게 없으면 처음 연 도구가 체크된다
    assert tp._checked_idx() == [1]
    from core.probe import probe
    extra = {"path": str(files["v"]), "info": probe(find_tool("ffprobe"), str(files["v"])), "kind": "video"}
    win.items.append(extra)
    tp.set_items(win.items)
    tp.panels[1]._list.insertItem(0, tp.panels[1]._list.takeItem(1))   # 순서 바꾸기
    assert tp.panels[1].file_order()[0] == str(files["v"])
    tp._run()
    wait_done(app, win)
    assert win._ok_outs


# ------------------------------------------------------------------ 여러 도구를 한 번에 / 재생
def test_run_needs_a_checked_tool(app, win, files):
    win._open_module("video")
    win._add_files([str(files["v"])])
    tp = win.tool_page
    assert tp._checked_idx() == [] and not tp.go.isEnabled()      # 아직 아무것도 체크 안 함
    tp._on_chip_clicked(2)                                         # 처음 연 도구가 자동으로 체크됨
    assert tp._checked_idx() == [2] and tp.go.isEnabled()
    tp._on_chip_clicked(3)                                         # 이미 체크된 게 있으면 보기만 한다
    assert tp._checked_idx() == [2]
    tp.chips[2].set_checked(False)
    assert not tp.go.isEnabled()


def test_changing_an_option_checks_the_tool(app, win, files):
    win._open_module("photo")
    win._add_files([str(files["i"])])
    tp = win.tool_page
    assert tp._checked_idx() == []
    tp.panels[1]._set("rotate", "180")                             # 회전/뒤집기 옵션을 만짐
    assert tp._checked_idx() == [1]


def test_chain_of_tools_runs_in_one_go(app, win, files):
    """한 번 올린 음악에 자르기 + 볼륨을 같이 적용: 결과 하나, 임시 파일은 남지 않는다."""
    from core.probe import probe
    win._open_module("audio")
    win._add_files([str(files["a"])])
    tp = win.tool_page
    tp.panels[0]._edits["start"].setText("1")
    tp.panels[0]._edits["end"].setText("3")
    tp.panels[2]._set("volume", 200)
    assert tp._checked_idx() == [0, 2]
    assert "2" in tp.go.text()
    tp._run()
    wait_done(app, win)
    assert len(win._ok_outs) == 1 and len(win._results) == 1 and win._results[0][1]
    out = Path(win._ok_outs[0])
    assert out.exists() and out.stem.endswith("_edit")
    assert probe(find_tool("ffprobe"), str(out)).duration == pytest.approx(2.0, abs=0.3)
    assert win._tmp_dir is None
    assert not [p for p in out.parent.iterdir() if p.name.startswith(".swapeg-")]


def test_chain_reports_bad_step_before_running(app, win, files, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    shown = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: shown.append(a[2]))
    win._open_module("video")
    win._add_files([str(files["v"])])
    tp = win.tool_page
    tp.panels[0]._edits["start"].setText("1")                      # 자르기는 올바르게
    tp._on_chip_clicked(3)
    tp.chips[3].set_checked(True)                                  # 속도/FPS 는 기본값(바꿀 게 없음)
    tp._run()
    assert shown and not win.runner.running                        # 아무 작업도 시작하지 않고 알림


def test_player_loads_and_plays(app, win, files):
    from ui import player
    if not player.AVAILABLE:
        pytest.skip("QtMultimedia 없음")
    win._open_module("audio")
    win._add_files([str(files["a"])])
    tp = win.tool_page
    assert tp.player is not None and tp.player.loaded and tp.controls.isVisible()
    tp._toggle_play()
    t = time.time()
    while time.time() - t < 5 and tp.player.position_seconds() < 0.2:
        app.processEvents()
        time.sleep(0.02)
    pos = tp.player.position_seconds()
    tp.player.pause()
    if pos < 0.2:
        pytest.skip("이 환경에서는 소리 장치가 없어 재생 위치가 움직이지 않음")
    assert tp.range._play is not None                              # 재생 위치선이 따라 움직인다
    win._reset()                                                   # 화면을 떠나면 파일을 놓아 준다
    assert not tp.player.loaded
