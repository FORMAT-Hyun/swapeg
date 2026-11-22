"""ffprobe로 미디어 정보 조회."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

from .i18n import tr


@dataclass
class MediaInfo:
    duration: float | None = None
    width: int | None = None
    height: int | None = None
    vcodec: str | None = None
    acodec: str | None = None
    fps: float | None = None
    sample_rate: int | None = None

    def summary(self) -> str:
        parts = []
        if self.width and self.height:
            parts.append(f"{self.width}x{self.height}")
        if self.vcodec:
            parts.append(self.vcodec)
        if self.acodec:
            parts.append(self.acodec)
        if self.duration is not None:
            m, s = divmod(int(self.duration), 60)
            h, m = divmod(m, 60)
            parts.append(f"{h}:{m:02d}:{s:02d}")
        return " · ".join(parts) or tr("정보 없음")


def _fps(text: str | None) -> float | None:
    try:
        a, _, b = (text or "").partition("/")
        v = float(a) / float(b or 1)
        return v if v > 0 else None
    except (ValueError, ZeroDivisionError):
        return None


def probe(ffprobe: str, path: str) -> MediaInfo:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        res = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", path],
            capture_output=True, timeout=30, creationflags=flags)
        data = json.loads(res.stdout.decode("utf-8", "replace") or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return MediaInfo()

    info = MediaInfo()
    try:
        info.duration = float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError):
        pass
    for st in data.get("streams", []):
        if st.get("codec_type") == "video" and info.vcodec is None:
            if st.get("disposition", {}).get("attached_pic"):
                continue
            info.vcodec = st.get("codec_name")
            info.width, info.height = st.get("width"), st.get("height")
            info.fps = _fps(st.get("avg_frame_rate") or st.get("r_frame_rate"))
        elif st.get("codec_type") == "audio" and info.acodec is None:
            info.acodec = st.get("codec_name")
            try:
                info.sample_rate = int(st.get("sample_rate"))
            except (TypeError, ValueError):
                pass
    return info
