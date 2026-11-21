"""ffmpeg / ffprobe 실행 파일 위치 탐색."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[2]


def find_tool(name: str, custom_dir: str | None = None) -> str | None:
    """사용자 지정 폴더 -> 앱의 bin 폴더 -> PATH 순으로 찾는다."""
    exe = name + (".exe" if sys.platform == "win32" else "")
    candidates = []
    if custom_dir:
        candidates.append(Path(custom_dir) / exe)
    candidates.append(app_dir() / "bin" / exe)
    for c in candidates:
        if c.is_file():
            return str(c)
    return shutil.which(name)
