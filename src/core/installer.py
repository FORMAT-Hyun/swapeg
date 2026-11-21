"""ffmpeg 자동 설치: 다운로드 -> SHA-256 검증 -> bin/ 폴더에 ffmpeg.exe, ffprobe.exe 추출."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from PySide6.QtCore import QThread, Signal

# gyan.dev 릴리스 빌드 (GPL, libx264/libx265 포함). 같은 주소 + ".sha256" 에 해시가 있다.
DEFAULT_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
WANTED = ("ffmpeg.exe", "ffprobe.exe")
_HEADERS = {"User-Agent": "Swapeg"}


class Cancelled(Exception):
    pass


class InstallWorker(QThread):
    progress = Signal(int, int)   # 받은 바이트, 전체 바이트(모르면 0)
    status = Signal(str)
    finished_ok = Signal(str)     # 설치된 bin 폴더
    failed = Signal(str)

    def __init__(self, dest_dir: Path, url: str = DEFAULT_URL, parent=None):
        super().__init__(parent)
        self.dest_dir = Path(dest_dir)
        self.url = url
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="swapeg-"))
        try:
            self.status.emit("체크섬 확인 중...")
            expected = self._fetch_hash()
            zip_path = tmp / "ffmpeg.zip"
            self.status.emit("ffmpeg 다운로드 중...")
            self._download(zip_path, expected)
            self.status.emit("압축 해제 중...")
            self._extract(zip_path)
            self.finished_ok.emit(str(self.dest_dir))
        except Cancelled:
            self.failed.emit("취소되었습니다.")
        except Exception as e:  # 네트워크/디스크/해시 오류 모두 사용자에게 메시지로 전달
            self.failed.emit(str(e))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    def _fetch_hash(self) -> str:
        req = urllib.request.Request(self.url + ".sha256", headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read(4096).decode("ascii", "ignore").strip()
        digest = text.split()[0].lower() if text else ""
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise RuntimeError("체크섬 정보를 가져오지 못했습니다.")
        return digest

    def _download(self, target: Path, expected: str) -> None:
        req = urllib.request.Request(self.url, headers=_HEADERS)
        h = hashlib.sha256()
        done = 0
        with urllib.request.urlopen(req, timeout=30) as r, open(target, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            while True:
                if self._cancel:
                    raise Cancelled
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                h.update(chunk)
                done += len(chunk)
                self.progress.emit(done, total)
        if h.hexdigest() != expected:
            raise RuntimeError("다운로드 파일의 체크섬이 일치하지 않습니다. (파일 손상 또는 변조 가능성)")

    def _extract(self, zip_path: Path) -> None:
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        found = set()
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                p = PurePosixPath(info.filename)
                # 경로 조작 방지: 필요한 두 파일만, 이름만 사용해서 bin/ 안에 쓴다.
                if p.name in WANTED and p.parent.name == "bin":
                    part = self.dest_dir / (p.name + ".part")
                    with z.open(info) as src, open(part, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    os.replace(part, self.dest_dir / p.name)
                    found.add(p.name)
        if set(WANTED) - found:
            raise RuntimeError("압축 파일에서 ffmpeg.exe/ffprobe.exe를 찾지 못했습니다.")
