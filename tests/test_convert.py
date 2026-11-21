"""실제 ffmpeg로 변환 조합을 검증한다 (bin/ffmpeg.exe 가 없으면 건너뜀)."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import simple  # noqa: E402
from core.ffpath import find_tool  # noqa: E402
from core.probe import probe  # noqa: E402

FF, FP = find_tool("ffmpeg"), find_tool("ffprobe")
pytestmark = pytest.mark.skipif(not FF, reason="ffmpeg 없음")


def run(args):
    subprocess.run(args, check=True, capture_output=True)


@pytest.fixture(scope="module")
def samples(tmp_path_factory):
    d = tmp_path_factory.mktemp("샘플 폴더")
    v, a, i = d / "영상 1.mp4", d / "소리.wav", d / "그림.png"
    run([FF, "-y", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=25:duration=2",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=2", "-c:v", "libx264",
         "-pix_fmt", "yuv420p", "-c:a", "aac", str(v)])
    run([FF, "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=2", str(a)])
    run([FF, "-y", "-f", "lavfi", "-i", "color=c=red@0.5:size=64x48,format=rgba",
         "-frames:v", "1", str(i)])
    return {"video": v, "audio": a, "image": i}


def convert(path, target):
    info = probe(FP, str(path))
    kind = simple.kind_of(str(path), info)
    assert simple.can_convert(kind, simple.ext_of(str(path)), target)
    out = simple.output_path(str(path), target)
    args = simple.build_args(FF, str(path), str(out), target, info, kind)
    r = subprocess.run(args, capture_output=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[-500:]
    assert out.exists() and out.stat().st_size > 0
    return out


@pytest.mark.parametrize("target", ["mp4", "mkv", "webm", "mov", "avi", "gif"])
def test_video_targets(samples, target):
    out = convert(samples["video"], target)
    info = probe(FP, str(out))
    assert info.width == (320 if target != "gif" else 320) and info.height == 240


@pytest.mark.parametrize("target", ["mp3", "wav", "flac", "m4a", "ogg"])
def test_audio_targets_from_video_and_audio(samples, target):
    assert probe(FP, str(convert(samples["video"], target))).duration
    assert probe(FP, str(convert(samples["audio"], target))).duration


@pytest.mark.parametrize("target", ["png", "jpg", "webp", "bmp", "tiff", "ico"])
def test_image_targets(samples, target):
    out = convert(samples["image"], target)
    assert probe(FP, str(out)).width == 64


def test_mp4_to_mkv_is_stream_copy(samples):
    info = probe(FP, str(samples["video"]))
    args = simple.build_args(FF, "i", "o.mkv", "mkv", info, "video")
    assert args.count("copy") == 2


def test_rules():
    assert not simple.can_convert("image", "png", "mp4")
    assert not simple.can_convert("audio", "mp3", "mp4")
    assert simple.can_convert("video", "mp4", "mp3")
    assert simple.can_convert("video", "gif", "png")
