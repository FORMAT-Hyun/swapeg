"""편집 도구를 실제 ffmpeg로 돌려 결과를 검증한다 (bin/ffmpeg.exe 가 없으면 건너뜀)."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import simple, tools  # noqa: E402
from core.ffpath import find_tool  # noqa: E402
from core.probe import probe  # noqa: E402

FF, FP = find_tool("ffmpeg"), find_tool("ffprobe")
pytestmark = pytest.mark.skipif(not FF, reason="ffmpeg 없음")


def sh(args):
    subprocess.run(args, check=True, capture_output=True)


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    d = tmp_path_factory.mktemp("편집 샘플")
    m = {"dir": d}
    m["v"] = d / "영상 하나.mp4"
    sh([FF, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=6", "-f", "lavfi",
        "-i", "sine=frequency=440:duration=6", "-c:v", "libx264", "-g", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", str(m["v"])])
    m["v2"] = d / "mute.mp4"
    sh([FF, "-y", "-f", "lavfi", "-i", "testsrc2=size=160x120:rate=30:duration=3", "-c:v", "libx264",
        "-pix_fmt", "yuv420p", str(m["v2"])])
    m["a"] = d / "소리 하나.wav"
    sh([FF, "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=6", str(m["a"])])
    m["a2"] = d / "second.mp3"
    sh([FF, "-y", "-f", "lavfi", "-i", "sine=frequency=550:duration=4", str(m["a2"])])
    m["img"] = d / "그림 하나.png"
    sh([FF, "-y", "-f", "lavfi", "-i", "color=c=red@0.6:size=200x100,format=rgba", "-frames:v", "1", str(m["img"])])
    m["logo"] = d / "logo.png"
    sh([FF, "-y", "-f", "lavfi", "-i", "color=c=blue:size=40x40", "-frames:v", "1", str(m["logo"])])
    m["srt"] = d / "자막 파일.srt"
    m["srt"].write_text("1\n00:00:00,500 --> 00:00:03,000\nHello 안녕하세요\n", encoding="utf-8")
    return m


def item(path):
    info = probe(FP, str(path))
    return {"path": str(path), "info": info, "kind": simple.kind_of(str(path), info)}


def run(tool_id, files, overrides=None, out_ext="", quality="original", out_dir=None):
    tool = tools.tool_by_id(tool_id)
    p = tools.defaults(tool)
    p.update(overrides or {})
    plans = tools.plan_jobs(tool, FF, [item(f) for f in files], p, out_ext, quality, out_dir)
    outs = []
    for pl in plans:
        r = subprocess.run(pl.args, capture_output=True)
        assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[-600:]
        assert Path(pl.output).stat().st_size > 0
        outs.append(Path(pl.output))
    return outs


def streams(path):
    r = subprocess.run([FP, "-v", "quiet", "-print_format", "json", "-show_streams", str(path)],
                       capture_output=True, check=True)
    return [s["codec_type"] for s in json.loads(r.stdout)["streams"]]


# ------------------------------------------------------------------ 동영상
def test_video_trim(media):
    out = run("v_trim", [media["v"]], {"start": "1", "end": "3.5"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(2.5, abs=0.4)
    assert "audio" in streams(out)


def test_video_trim_fast_copy(media):
    out = run("v_trim", [media["v"]], {"start": "2", "fast": True})[0]
    assert probe(FP, str(out)).duration == pytest.approx(4.0, abs=0.7)   # 키프레임 단위로 잘린다


def test_video_trim_errors(media):
    with pytest.raises(tools.ToolError):
        run("v_trim", [media["v"]], {"start": "4", "end": "2"})
    with pytest.raises(tools.ToolError):
        run("v_trim", [media["v"]], {"start": "abc"})
    with pytest.raises(tools.ToolError):
        run("v_trim", [media["v"]], {})


def test_video_merge_with_silent_clip(media):
    out = run("v_merge", [media["v"], media["v2"]])[0]
    info = probe(FP, str(out))
    assert info.duration == pytest.approx(9.0, abs=0.6)
    assert (info.width, info.height) == (320, 240)      # 첫 번째 영상 기준
    assert "audio" in streams(out)
    with pytest.raises(tools.ToolError):
        run("v_merge", [media["v"]])


def test_video_transform(media):
    out = run("v_transform", [media["v"]], {"res": "120"})[0]
    assert probe(FP, str(out)).height == 120
    out = run("v_transform", [media["v"]], {"rotate": "90"})[0]
    i = probe(FP, str(out))
    assert (i.width, i.height) == (240, 320)
    out = run("v_transform", [media["v"]], {"ratio": "1:1", "flip": "h"})[0]
    i = probe(FP, str(out))
    assert i.width == i.height
    out = run("v_transform", [media["v"]], {"ratio": "custom", "cw": "100", "ch": "80", "cx": "10", "cy": "10"})[0]
    i = probe(FP, str(out))
    assert (i.width, i.height) == (100, 80)
    with pytest.raises(tools.ToolError):
        run("v_transform", [media["v"]], {})


def test_video_speed_and_fps(media):
    out = run("v_speed", [media["v"]], {"speed": "2"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(3.0, abs=0.5)
    out = run("v_speed", [media["v"]], {"speed": "0.5", "fps": "10"})[0]
    i = probe(FP, str(out))
    assert i.duration == pytest.approx(12.0, abs=1.0) and i.fps == pytest.approx(10, abs=0.5)
    with pytest.raises(tools.ToolError):
        run("v_speed", [media["v"]], {})


def test_video_audio_modes(media):
    out = run("v_audio", [media["v"]], {"mode": "remove"})[0]
    assert "audio" not in streams(out)
    out = run("v_audio", [media["v"]], {"mode": "replace", "audio_file": str(media["a2"])})[0]
    assert "audio" in streams(out) and probe(FP, str(out)).duration == pytest.approx(4.0, abs=0.5)
    out = run("v_audio", [media["v"]], {"mode": "keep", "volume": 50})[0]
    assert "audio" in streams(out)
    with pytest.raises(tools.ToolError):
        run("v_audio", [media["v"]], {"mode": "replace"})
    with pytest.raises(tools.ToolError):
        run("v_audio", [media["v"]], {"mode": "keep", "volume": 100})


def test_video_subtitles(media):
    out = run("v_subs", [media["v"]], {"mode": "burn", "sub_file": str(media["srt"])})[0]
    assert probe(FP, str(out)).vcodec == "h264"
    out = run("v_subs", [media["v"]], {"mode": "track", "sub_file": str(media["srt"])})[0]
    assert "subtitle" in streams(out)
    out2 = run("v_subs", [out], {"mode": "remove"})[0]
    assert "subtitle" not in streams(out2)
    with pytest.raises(tools.ToolError):
        run("v_subs", [media["v"]], {"mode": "track", "sub_file": str(media["srt"])}, out_ext="avi")
    with pytest.raises(tools.ToolError):
        run("v_subs", [media["v"]], {"mode": "burn"})


def test_video_tool_changes_container(media):
    out = run("v_transform", [media["v"]], {"res": "120"}, out_ext="webm")[0]
    assert out.suffix == ".webm" and probe(FP, str(out)).vcodec == "vp9"


# ------------------------------------------------------------------ 음악
def test_audio_trim_and_fade(media):
    out = run("a_trim", [media["a"]], {"start": "1", "end": "4"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(3.0, abs=0.2)
    out = run("a_trim", [media["a2"]], {"start": "1", "fade": "both"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(3.0, abs=0.3)
    with pytest.raises(tools.ToolError):
        run("a_trim", [media["a"]], {"end": "1.5", "fade": "both"})


def test_audio_trim_from_video_file(media):
    out = run("a_trim", [media["v"]], {"start": "1", "end": "3"}, out_ext="mp3")[0]
    assert out.suffix == ".mp3" and streams(out) == ["audio"]


@pytest.mark.parametrize("mode,expected", [("none", 10.0), ("gap", 11.0), ("cross", 8.0)])
def test_audio_merge_modes(media, mode, expected):
    out = run("a_merge", [media["a"], media["a2"]], {"mode": mode}, out_ext="mp3")[0]
    assert probe(FP, str(out)).duration == pytest.approx(expected, abs=0.5)


def test_audio_volume_and_speed(media):
    assert run("a_volume", [media["a"]], {"volume": 50})[0].exists()
    assert run("a_volume", [media["a"]], {"volume": 100, "norm": "on"})[0].exists()
    out = run("a_speed", [media["a"]], {"speed": "2"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(3.0, abs=0.3)
    out = run("a_speed", [media["a"]], {"speed": "0.5", "pitch": "change"})[0]
    assert probe(FP, str(out)).duration == pytest.approx(12.0, abs=0.8)
    with pytest.raises(tools.ToolError):
        run("a_volume", [media["a"]], {"volume": 100})
    with pytest.raises(tools.ToolError):
        run("a_speed", [media["a"]], {"speed": "1"})


# ------------------------------------------------------------------ 사진
def test_photo_resize(media):
    out = run("p_resize", [media["img"]], {"quick": "50"})[0]
    i = probe(FP, str(out))
    assert (i.width, i.height) == (100, 50)
    out = run("p_resize", [media["img"]], {"quick": "custom", "w": "80", "h": ""})[0]
    assert (probe(FP, str(out)).width, probe(FP, str(out)).height) == (80, 40)
    out = run("p_resize", [media["img"]], {"quick": "custom", "w": "50", "h": "50", "keep": "free"})[0]
    assert (probe(FP, str(out)).width, probe(FP, str(out)).height) == (50, 50)
    out = run("p_resize", [media["img"]], {"quick": "custom", "w": "50", "h": "50", "keep": "keep"})[0]
    assert (probe(FP, str(out)).width, probe(FP, str(out)).height) == (50, 25)
    with pytest.raises(tools.ToolError):
        run("p_resize", [media["img"]], {"quick": "custom"})


def test_photo_rotate_crop_mark(media):
    out = run("p_rotate", [media["img"]], {"rotate": "90"})[0]
    assert (probe(FP, str(out)).width, probe(FP, str(out)).height) == (100, 200)
    out = run("p_crop", [media["img"]], {"ratio": "1:1"})[0]
    assert probe(FP, str(out)).width == probe(FP, str(out)).height
    out = run("p_mark", [media["img"]], {"logo": str(media["logo"]), "pos": 0, "size": "30"})[0]
    assert (probe(FP, str(out)).width, probe(FP, str(out)).height) == (200, 100)
    with pytest.raises(tools.ToolError):
        run("p_mark", [media["img"]], {})


@pytest.mark.parametrize("ext", ["jpg", "webp", "gif", "bmp", "ico", "png"])
def test_photo_tool_other_formats(media, ext):
    out = run("p_rotate", [media["img"]], {"rotate": "180"}, out_ext=ext)[0]
    assert out.suffix == "." + ext and probe(FP, str(out)).width


def test_quality_and_output_dir(media, tmp_path):
    big = run("v_transform", [media["v"]], {"res": "120"}, quality="original", out_dir=str(tmp_path))[0]
    small = run("v_transform", [media["v"]], {"res": "120"}, quality="small", out_dir=str(tmp_path))[0]
    assert big.parent == tmp_path and small.stat().st_size <= big.stat().st_size


def test_batch_makes_one_output_per_file(media):
    outs = run("p_rotate", [media["img"], media["logo"]], {"rotate": "90"})
    assert len(outs) == 2


def test_rejects_wrong_kind(media):
    with pytest.raises(tools.ToolError):
        run("v_trim", [media["a"]], {"start": "1"})
    with pytest.raises(tools.ToolError):
        run("p_rotate", [media["v"]], {"rotate": "90"})


def test_specs_are_consistent():
    ids = [t.id for ts in tools.TOOLS.values() for t in ts]
    assert len(ids) == len(set(ids)) == len(tools._BUILDERS)
    for ts in tools.TOOLS.values():
        for t in ts:
            p = tools.defaults(t)
            for f in t.fields:
                if f.kind == "seg":
                    assert f.default in [v for v, _ in f.options], (t.id, f.key)
                if f.show_if:
                    assert f.show_if[0] in p or f.show_if[0] in {x.key for x in t.fields}, (t.id, f.key)
