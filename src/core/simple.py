"""간단 변환: 파일 + 출력 확장자만 정하면 '원본 화질 유지' 설정으로 ffmpeg 인자를 만든다.

원칙
- 컨테이너가 코덱을 그대로 담을 수 있으면 재인코딩 없이 복사(무손실, 빠름)
- 재인코딩이 필요하면 눈으로 구분이 안 되는 고화질 설정, 해상도/FPS는 원본 유지
"""
from __future__ import annotations

from pathlib import Path

from .probe import MediaInfo

IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff", "ico", "jfif"}
AUDIO_EXTS = {"mp3", "wav", "flac", "m4a", "aac", "ogg", "opus", "wma"}

# (확장자, 표시 이름, 종류)
FORMATS: list[tuple[str, str, str]] = [
    ("mp4", "MP4 · 영상", "video"),
    ("mkv", "MKV · 영상", "video"),
    ("webm", "WebM · 영상", "video"),
    ("mov", "MOV · 영상", "video"),
    ("avi", "AVI · 영상", "video"),
    ("gif", "GIF · 움짤", "video"),
    ("mp3", "MP3 · 오디오", "audio"),
    ("wav", "WAV · 오디오", "audio"),
    ("flac", "FLAC · 오디오", "audio"),
    ("m4a", "M4A · 오디오", "audio"),
    ("ogg", "OGG · 오디오", "audio"),
    ("png", "PNG · 이미지", "image"),
    ("jpg", "JPG · 이미지", "image"),
    ("webp", "WebP · 이미지", "image"),
    ("bmp", "BMP · 이미지", "image"),
    ("tiff", "TIFF · 이미지", "image"),
    ("ico", "ICO · 아이콘", "image"),
]
TARGET_KIND = {ext: kind for ext, _label, kind in FORMATS}

# 컨테이너별로 '그대로 복사'해도 되는 코덱 (None = 전부 허용)
COPY_OK: dict[str, tuple[set[str] | None, set[str] | None]] = {
    "mp4": ({"h264", "hevc", "mpeg4", "av1"}, {"aac", "mp3", "ac3", "eac3", "opus"}),
    "mov": ({"h264", "hevc", "mpeg4", "prores", "mjpeg"},
            {"aac", "mp3", "ac3", "pcm_s16le", "pcm_s24le", "alac"}),
    "mkv": (None, None),
    "webm": ({"vp8", "vp9", "av1"}, {"opus", "vorbis"}),
    "avi": ({"mpeg4", "mjpeg", "msmpeg4v3"}, {"mp3", "ac3", "pcm_s16le"}),
}


def ext_of(path: str) -> str:
    return Path(path).suffix.lower().lstrip(".")


def kind_of(path: str, info: MediaInfo) -> str:
    ext = ext_of(path)
    if ext in IMAGE_EXTS:
        return "image"
    if info.vcodec is None and info.acodec:
        return "audio"
    if ext in AUDIO_EXTS:
        return "audio"
    return "video"


def can_convert(kind: str, src_ext: str, target: str) -> bool:
    tk = TARGET_KIND.get(target)
    if tk == "video":
        return kind == "video"
    if tk == "audio":
        return kind in ("video", "audio")
    if tk == "image":
        return kind == "image" or src_ext == "gif"  # 움짤의 첫 장면을 이미지로
    return False


def output_path(src: str, ext: str) -> Path:
    """원본과 같은 폴더에 같은 이름으로. 겹치면 _converted, _1 ... 를 붙인다."""
    s = Path(src)
    out = s.with_suffix("." + ext)
    if out.exists() or out.resolve() == s.resolve():
        out = s.with_name(f"{s.stem}_converted.{ext}")
    i = 1
    while out.exists():
        out = s.with_name(f"{s.stem}_converted_{i}.{ext}")
        i += 1
    return out


def _can_copy(codec: str | None, allowed: set[str] | None) -> bool:
    return codec is not None and (allowed is None or codec in allowed)


_BASE = ["-hide_banner", "-nostdin", "-n", "-progress", "pipe:1", "-nostats"]


def build_args(ffmpeg: str, src: str, out: str, target: str, info: MediaInfo, kind: str) -> list[str]:
    tk = TARGET_KIND[target]
    if tk == "video":
        return _video(ffmpeg, src, out, target, info)
    if tk == "audio":
        return _audio(ffmpeg, src, out, target, info)
    return _image(ffmpeg, src, out, target)


def _video(ffmpeg, src, out, target, info) -> list[str]:
    args = [ffmpeg, *_BASE, "-i", src]
    if target == "gif":
        chain = ("fps=15,scale='min(720,iw)':-1:flags=lanczos,split[s0][s1];"
                 "[s0]palettegen[p];[s1][p]paletteuse")
        return args + ["-filter_complex", chain, "-an", "-loop", "0", out]

    v_ok, a_ok = COPY_OK[target]
    args += ["-map", "0:v:0?", "-map", "0:a?", "-sn", "-map_metadata", "0"]
    if _can_copy(info.vcodec, v_ok):
        args += ["-c:v", "copy"]
    elif target == "webm":
        args += ["-c:v", "libvpx-vp9", "-crf", "15", "-b:v", "0", "-deadline", "good",
                 "-cpu-used", "2", "-row-mt", "1", "-pix_fmt", "yuv420p"]
    else:
        args += ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"]

    if info.acodec is None:
        args += ["-an"]
    elif _can_copy(info.acodec, a_ok):
        args += ["-c:a", "copy"]
    elif target == "webm":
        args += ["-c:a", "libopus", "-b:a", "256k"]
    elif target == "avi":
        args += ["-c:a", "libmp3lame", "-b:a", "320k"]
    else:
        args += ["-c:a", "aac", "-b:a", "320k"]

    if target in ("mp4", "mov"):
        args += ["-movflags", "+faststart"]
    return args + [out]


def _audio(ffmpeg, src, out, target, info) -> list[str]:
    args = [ffmpeg, *_BASE, "-i", src, "-vn", "-map", "0:a:0", "-map_metadata", "0"]
    if target == "mp3":
        args += ["-c:a", "copy"] if info.acodec == "mp3" else ["-c:a", "libmp3lame", "-q:a", "0"]
    elif target == "wav":
        args += ["-c:a", "pcm_s16le"]
    elif target == "flac":
        args += ["-c:a", "flac"]
    elif target == "m4a":
        args += ["-c:a", "copy"] if info.acodec == "aac" else ["-c:a", "aac", "-b:a", "320k"]
    elif target == "ogg":
        args += ["-c:a", "libvorbis", "-q:a", "8"]
    return args + [out]


# 투명 배경을 흰색으로 깔아서 JPG로 저장 (JPG는 투명을 지원하지 않음)
_FLATTEN = "split=2[bg][fg];[bg]drawbox=c=white@1:replace=1:t=fill[bg];[bg][fg]overlay=format=auto,format=rgb24"


def _image(ffmpeg, src, out, target) -> list[str]:
    args = [ffmpeg, *_BASE, "-i", src, "-frames:v", "1", "-update", "1"]
    if target == "jpg":
        args += ["-filter_complex", _FLATTEN, "-q:v", "1", "-pix_fmt", "yuvj444p"]
    elif target == "webp":
        args += ["-lossless", "1", "-compression_level", "6"]
    elif target == "png":
        args += ["-compression_level", "9"]
    elif target == "ico":
        args += ["-vf", "scale='min(256,iw)':'min(256,ih)':force_original_aspect_ratio=decrease"]
    return args + [out]
