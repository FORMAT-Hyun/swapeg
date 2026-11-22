"""간단 변환: 파일 + 출력 확장자만 정하면 '원본 화질 유지' 설정으로 ffmpeg 인자를 만든다.

원칙
- 컨테이너가 코덱을 그대로 담을 수 있으면 재인코딩 없이 복사(무손실, 빠름)
- 재인코딩이 필요하면 눈으로 구분이 안 되는 고화질 설정, 해상도/FPS는 원본 유지
"""
from __future__ import annotations

from pathlib import Path

from .probe import MediaInfo

# ---- 입력으로 인식하는 확장자 (그 외는 ffprobe 결과로 판단) ---------------------
IMAGE_EXTS = {"jpg", "jpeg", "jfif", "png", "webp", "bmp", "tif", "tiff", "ico", "tga", "ppm",
              "pgm", "pbm", "pam", "jp2", "j2k", "pcx", "sgi", "qoi", "exr", "hdr", "avif",
              "jxl", "dds", "xbm", "xpm", "xwd", "psd", "apng"}
AUDIO_EXTS = {"mp3", "wav", "flac", "m4a", "aac", "ogg", "oga", "opus", "wma", "aiff", "aif",
              "ac3", "eac3", "mp2", "mka", "au", "caf", "wv", "tta", "amr", "ape", "dts",
              "ra", "spx", "mpc", "m4b", "weba"}

# ---- 출력 형식 ---------------------------------------------------------------
VIDEO_TARGETS = ["mp4", "mkv", "webm", "mov", "avi", "m4v", "wmv", "asf", "flv", "3gp", "3g2",
                 "ts", "mts", "m2ts", "mpg", "mpeg", "vob", "ogv", "gif", "apng"]
AUDIO_TARGETS = ["mp3", "wav", "flac", "m4a", "aac", "ogg", "oga", "opus", "wma", "aiff", "aif",
                 "ac3", "mp2", "mka", "au", "caf", "wv", "tta"]
# GIF는 영상(움짤)과 이미지(정지 GIF) 양쪽에 모두 있다
IMAGE_TARGETS = ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff", "tif", "ico", "tga", "ppm",
                 "jp2", "pcx", "sgi", "qoi", "exr", "avif"]

# 화면에 버튼으로 항상 보여 줄 자주 쓰는 형식 (나머지는 [더보기])
POPULAR = {
    "video": ["mp4", "mkv", "webm", "mov", "avi", "gif"],
    "audio": ["mp3", "wav", "flac", "m4a", "ogg", "opus"],
    "image": ["png", "jpg", "webp", "gif", "bmp", "tiff", "ico"],
}
DEFAULT = {"video": "mp4", "audio": "mp3", "image": "png"}

_NAMES = {"webm": "WebM", "webp": "WebP", "apng": "APNG", "tiff": "TIFF"}
FORMATS: list[tuple[str, str, str]] = (
    [(e, _NAMES.get(e, e.upper()), "video") for e in VIDEO_TARGETS]
    + [(e, _NAMES.get(e, e.upper()), "audio") for e in AUDIO_TARGETS]
    + [(e, _NAMES.get(e, e.upper()), "image") for e in IMAGE_TARGETS]
)
TARGET_KIND: dict[str, str] = {}   # 확장자 -> 기본 종류 (gif는 영상으로 취급, 이미지 쪽은 입력 종류로 구분)
for _e, _l, _k in FORMATS:
    TARGET_KIND.setdefault(_e, _k)
_LABELS = {e: label for e, label, _k in FORMATS}


def label_of(ext: str) -> str:
    return _LABELS.get(ext, ext.upper())


KIND_TITLE = {"video": "영상", "audio": "오디오", "image": "이미지"}

# ---- 영상 컨테이너별 규칙 -----------------------------------------------------
X264 = ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"]
VP9 = ["-c:v", "libvpx-vp9", "-crf", "15", "-b:v", "0", "-deadline", "good",
       "-cpu-used", "2", "-row-mt", "1", "-pix_fmt", "yuv420p"]
AAC = ["-c:a", "aac", "-b:a", "320k"]
MP3 = ["-c:a", "libmp3lame", "-b:a", "320k"]

_MP4_V = {"h264", "hevc", "mpeg4", "av1"}
_MP4_A = {"aac", "mp3", "ac3", "eac3", "opus"}
_TS_V = {"h264", "hevc", "mpeg2video"}
_TS_A = {"aac", "mp3", "ac3", "eac3", "mp2"}

# 확장자: (복사 가능한 영상 코덱, 복사 가능한 오디오 코덱, 영상 인코딩 인자, 오디오 인코딩 인자, 추가 인자)
#   복사 가능 코덱이 None 이면 전부 복사 허용
VIDEO_SPECS: dict[str, tuple] = {
    "mp4": (_MP4_V, _MP4_A, X264, AAC, ["-movflags", "+faststart"]),
    "m4v": (_MP4_V, _MP4_A, X264, AAC, ["-movflags", "+faststart"]),
    "mov": ({"h264", "hevc", "mpeg4", "prores", "mjpeg"},
            {"aac", "mp3", "ac3", "pcm_s16le", "pcm_s24le", "alac"}, X264, AAC,
            ["-movflags", "+faststart"]),
    "mkv": (None, None, X264, AAC, []),
    "webm": ({"vp8", "vp9", "av1"}, {"opus", "vorbis"}, VP9, ["-c:a", "libopus", "-b:a", "256k"], []),
    "avi": ({"mpeg4", "mjpeg", "msmpeg4v3"}, {"mp3", "ac3", "pcm_s16le"}, X264, MP3, []),
    "3gp": ({"h264", "mpeg4", "h263"}, {"aac"}, X264, AAC, []),
    "3g2": ({"h264", "mpeg4", "h263"}, {"aac"}, X264, AAC, []),
    "flv": ({"h264", "flv1"}, {"aac", "mp3"}, X264, AAC, []),
    "ts": (_TS_V, _TS_A, X264, AAC, ["-f", "mpegts"]),
    "mts": (_TS_V, _TS_A, X264, AAC, ["-f", "mpegts"]),
    "m2ts": (_TS_V, _TS_A, X264, AAC, ["-f", "mpegts"]),
    "wmv": ({"wmv1", "wmv2", "wmv3", "vc1"}, {"wmav2", "wmapro"},
            ["-c:v", "wmv2", "-qscale:v", "2", "-pix_fmt", "yuv420p"],
            ["-c:a", "wmav2", "-b:a", "320k"], ["-f", "asf"]),
    "asf": ({"wmv1", "wmv2", "wmv3", "vc1"}, {"wmav2", "wmapro"},
            ["-c:v", "wmv2", "-qscale:v", "2", "-pix_fmt", "yuv420p"],
            ["-c:a", "wmav2", "-b:a", "320k"], ["-f", "asf"]),
    "mpg": ({"mpeg1video", "mpeg2video"}, {"mp2", "mp3", "ac3"},
            ["-c:v", "mpeg2video", "-q:v", "2", "-pix_fmt", "yuv420p"],
            ["-c:a", "mp2", "-b:a", "384k"], ["-f", "mpeg"]),
    "mpeg": ({"mpeg1video", "mpeg2video"}, {"mp2", "mp3", "ac3"},
             ["-c:v", "mpeg2video", "-q:v", "2", "-pix_fmt", "yuv420p"],
             ["-c:a", "mp2", "-b:a", "384k"], ["-f", "mpeg"]),
    "vob": ({"mpeg2video"}, {"ac3", "mp2"},
            ["-c:v", "mpeg2video", "-q:v", "2", "-pix_fmt", "yuv420p"],
            ["-c:a", "ac3", "-b:a", "448k"], ["-f", "vob"]),
    "ogv": ({"theora"}, {"vorbis"}, ["-c:v", "libtheora", "-q:v", "10"],
            ["-c:a", "libvorbis", "-q:a", "8"], []),
}

# ---- 오디오 형식별 규칙: 확장자: (복사 가능 코덱(None=전부), 인코딩 인자, 추가 인자) -----
AUDIO_SPECS: dict[str, tuple] = {
    "mp3": ({"mp3"}, ["-c:a", "libmp3lame", "-q:a", "0"], []),
    "wav": (set(), ["-c:a", "pcm_s16le"], []),
    "flac": ({"flac"}, ["-c:a", "flac"], []),
    "m4a": ({"aac", "alac"}, AAC, []),
    "aac": ({"aac"}, AAC, ["-f", "adts"]),
    "ogg": ({"vorbis"}, ["-c:a", "libvorbis", "-q:a", "8"], []),
    "oga": ({"vorbis"}, ["-c:a", "libvorbis", "-q:a", "8"], ["-f", "ogg"]),
    "opus": ({"opus"}, ["-c:a", "libopus", "-b:a", "256k"], []),
    "wma": ({"wmav2"}, ["-c:a", "wmav2", "-b:a", "320k"], ["-f", "asf"]),
    "aiff": (set(), ["-c:a", "pcm_s16be"], []),
    "aif": (set(), ["-c:a", "pcm_s16be"], ["-f", "aiff"]),
    "ac3": ({"ac3"}, ["-c:a", "ac3", "-b:a", "640k"], []),
    "mp2": ({"mp2"}, ["-c:a", "mp2", "-b:a", "384k"], []),
    "mka": (None, ["-c:a", "flac"], []),
    "au": (set(), ["-c:a", "pcm_s16be"], []),
    "caf": (set(), ["-c:a", "pcm_s16le"], []),
    "wv": (set(), ["-c:a", "wavpack"], []),
    "tta": (set(), ["-c:a", "tta"], []),
}


# 오디오 트랙을 여러 개 담을 수 있는 컨테이너는 전부 유지, 나머지는 첫 트랙만
_MULTI_AUDIO = {"mp4", "m4v", "mov", "mkv", "webm", "ts", "mts", "m2ts"}


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


def can_convert(kind: str, src_ext: str, target: str, tk: str | None = None) -> bool:
    """kind: 입력 종류, target: 출력 확장자, tk: 출력 종류(화면에서 GIF처럼 두 종류에 있는 형식을 구분할 때)."""
    if src_ext == target:
        return False  # 같은 형식으로 바꾸는 건 의미가 없다
    if target == "gif" and tk is None:
        return kind in ("video", "image")
    tk = tk or TARGET_KIND.get(target)
    if tk == "video":
        return kind == "video"
    if tk == "audio":
        return kind in ("video", "audio")
    if tk == "image":
        return kind == "image" or src_ext == "gif"  # 움짤의 첫 장면을 이미지로
    return False


def output_path(src: str, ext: str, out_dir: str | None = None) -> Path:
    """기본은 원본과 같은 폴더(out_dir 지정 시 그 폴더)에 같은 이름으로. 겹치면 _converted, _1 ... 를 붙인다."""
    s = Path(src)
    folder = Path(out_dir) if out_dir else s.parent
    out = folder / f"{s.stem}.{ext}"
    if out.exists() or out.resolve() == s.resolve():
        out = folder / f"{s.stem}_converted.{ext}"
    i = 1
    while out.exists():
        out = folder / f"{s.stem}_converted_{i}.{ext}"
        i += 1
    return out


# ---- 화질 설정 -------------------------------------------------------------
QUALITY_LEVELS = [
    ("original", "원본 화질 유지", "가장 선명하고 용량이 큽니다 (기본)"),
    ("balanced", "균형", "화질 차이는 거의 없고 용량이 줄어듭니다"),
    ("small", "작은 용량", "용량을 크게 줄입니다. 화질이 조금 떨어질 수 있습니다"),
]
_CRF = {"libx264": {"balanced": "21", "small": "26"}, "libx265": {"balanced": "24", "small": "29"},
        "libvpx-vp9": {"balanced": "30", "small": "36"}}
_ABITRATE = {"balanced": "192k", "small": "128k"}
_QA = {"libmp3lame": {"balanced": "2", "small": "4"}, "libvorbis": {"balanced": "5", "small": "3"}}
_QV = {"mjpeg": {"balanced": "3", "small": "6"}, "mpeg2video": {"balanced": "4", "small": "8"},
       "wmv2": {"balanced": "4", "small": "8"}, "libtheora": {"balanced": "7", "small": "5"}}


def _tune(args: list[str], quality: str) -> list[str]:
    """화질 설정을 인코딩 인자에 반영한다. 'original'이면 그대로. 무손실 형식(FLAC/WAV/PNG)은 건드리지 않는다."""
    if quality not in ("balanced", "small"):
        return args
    out = list(args)
    vcodec = acodec = None
    for i, a in enumerate(out[:-1]):
        if a == "-c:v":
            vcodec = out[i + 1]
        elif a == "-c:a":
            acodec = out[i + 1]
    for i, a in enumerate(out[:-1]):
        nxt = out[i + 1]
        if a == "-crf" and vcodec in _CRF:
            out[i + 1] = _CRF[vcodec][quality]
        elif a == "-b:a" and acodec in ("aac", "libopus", "libmp3lame", "mp2", "wmav2", "ac3"):
            out[i + 1] = _ABITRATE[quality]
        elif a == "-q:a" and acodec in _QA:
            out[i + 1] = _QA[acodec][quality]
        elif a in ("-q:v", "-qscale:v") and (vcodec in _QV or nxt == "1"):
            out[i + 1] = _QV.get(vcodec, _QV["mjpeg"])[quality]  # vcodec 없는 jpg 출력은 mjpeg 취급
    if "-lossless" in out:  # WebP: 무손실 -> 고품질 손실 압축
        i = out.index("-lossless")
        out[i + 1] = "0"
        out[i + 2:i + 2] = ["-quality", "90" if quality == "balanced" else "75"]
    return out


def _can_copy(codec: str | None, allowed: set[str] | None) -> bool:
    return codec is not None and (allowed is None or codec in allowed)


_BASE = ["-hide_banner", "-nostdin", "-n", "-progress", "pipe:1", "-nostats"]


def build_args(ffmpeg: str, src: str, out: str, target: str, info: MediaInfo, kind: str,
               quality: str = "original") -> list[str]:
    tk = TARGET_KIND[target]
    if target == "gif" and kind == "image":
        tk = "image"  # 정지 이미지 -> GIF
    if tk == "video":
        args = _video(ffmpeg, src, out, target, info)
    elif tk == "audio":
        args = _audio(ffmpeg, src, out, target, info)
    else:
        args = _image(ffmpeg, src, out, target)
    return _tune(args, quality)


def _video(ffmpeg, src, out, target, info) -> list[str]:
    args = [ffmpeg, *_BASE, "-i", src]
    if target in ("gif", "apng"):
        scale = "fps=15,scale='min(720,iw)':-1:flags=lanczos"
        if target == "gif":
            chain = scale + ",split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
            return args + ["-filter_complex", chain, "-an", "-loop", "0", out]
        return args + ["-vf", scale, "-an", "-plays", "0", "-f", "apng", out]

    v_ok, a_ok, v_enc, a_enc, extra = VIDEO_SPECS[target]
    audio_map = "0:a?" if target in _MULTI_AUDIO else "0:a:0?"
    args += ["-map", "0:v:0?", "-map", audio_map, "-sn", "-map_metadata", "0"]
    args += ["-c:v", "copy"] if _can_copy(info.vcodec, v_ok) else v_enc
    if info.acodec is None:
        args += ["-an"]
    elif _can_copy(info.acodec, a_ok):
        args += ["-c:a", "copy"]
    else:
        args += a_enc
    return args + extra + [out]


def _audio(ffmpeg, src, out, target, info) -> list[str]:
    copy_ok, enc, extra = AUDIO_SPECS[target]
    args = [ffmpeg, *_BASE, "-i", src, "-vn", "-map", "0:a:0", "-map_metadata", "0"]
    args += ["-c:a", "copy"] if _can_copy(info.acodec, copy_ok) else enc
    return args + extra + [out]


# 투명 배경을 흰색으로 깔아서 저장 (JPG 등은 투명을 지원하지 않음)
_FLATTEN = "split=2[bg][fg];[bg]drawbox=c=white@1:replace=1:t=fill[bg];[bg][fg]overlay=format=auto,format=rgb24"


def image_codec_opts(target: str) -> list[str]:
    """이미지 형식별 인코딩 옵션 (필터는 제외)."""
    if target in ("jpg", "jpeg"):
        return ["-q:v", "1", "-pix_fmt", "yuvj444p"]
    if target == "webp":
        return ["-lossless", "1", "-compression_level", "6"]
    if target == "png":
        return ["-compression_level", "9"]
    if target == "avif":
        return ["-crf", "0"]
    return []


_GIF_PALETTE = "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"   # 256색 팔레트를 이미지에 맞춰 생성
_ICO_SCALE = "scale='min(256,iw)':'min(256,ih)':force_original_aspect_ratio=decrease"


def _image(ffmpeg, src, out, target) -> list[str]:
    args = [ffmpeg, *_BASE, "-i", src, "-frames:v", "1", "-update", "1"]
    if target in ("jpg", "jpeg"):
        args += ["-filter_complex", _FLATTEN]
    elif target == "gif":
        args += ["-filter_complex", _GIF_PALETTE]
    elif target == "ico":
        args += ["-vf", _ICO_SCALE]
    return args + image_codec_opts(target) + [out]
