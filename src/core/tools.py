"""편집 도구(동영상 / 음악 / 사진): 도구 사양(화면용) + ffmpeg 명령 생성.

- 사양(Tool/Field)은 화면이 그대로 읽어서 옵션 패널을 만든다 (Qt에 의존하지 않음).
- plan_jobs()가 입력 파일과 옵션 값으로 실행할 ffmpeg 명령(Plan) 목록을 만든다.
- 화질 설정(원본/균형/작은 용량)은 simple._tune 을 그대로 재사용한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import simple
from .i18n import tr


class ToolError(Exception):
    """사용자가 고칠 수 있는 입력 오류 (화면에 그대로 보여 준다)."""


# ===================================================================== 사양
@dataclass
class Field:
    key: str
    kind: str            # seg slider check note time2 size crop pick files pos9
    label: str = ""
    options: list = field(default_factory=list)     # seg: [(값, 한국어 라벨)]
    default: Any = None
    min: int = 0
    max: int = 100
    unit: str = ""
    show_if: tuple | None = None                    # (다른 필드 key, 값 또는 값 튜플)
    pick_title: str = ""
    pick_filter: str = ""


@dataclass
class Tool:
    id: str
    module: str          # video | audio | photo
    name: str
    icon: str
    btn: str
    suffix: str
    fields: list[Field]
    multi: bool = False  # True면 모든 입력 파일을 합쳐 결과 하나를 만든다


@dataclass
class Plan:
    args: list[str]
    output: str
    duration: float | None
    src: dict            # 미리보기에 쓸 입력 항목 {path, info, kind}
    final: bool = True   # False면 다음 단계로 넘기는 임시 결과
    group: int = 0       # 같은 최종 결과를 만드는 단계들은 같은 번호
    step: int = 0
    steps: int = 1
    label: str = ""      # 진행 화면에 보일 단계 이름 (한국어 원문)
    prepare: Any = None  # 두 번째 단계부터: 실행 직전에 앞 단계 결과를 보고 args 를 채운다 (Plan 을 받음)


MODULES = {
    "video": ("동영상", "video"),
    "audio": ("음악", "audio"),
    "photo": ("사진", "image"),
    "convert": ("형식 변환", "swap"),      # 도구 묶음 이름 (화면 구역 제목)
}
KIND_MODULE = {"video": "video", "audio": "audio", "image": "photo"}   # 파일 종류 -> 쓸 수 있는 도구 묶음
MODULE_EXTS = {
    "video": set(simple.VIDEO_SPECS),
    "audio": set(simple.AUDIO_SPECS),
    "photo": set(simple.IMAGE_TARGETS),
}
MODULE_KIND = {"video": "video", "audio": "audio", "photo": "image"}   # 형식 목록의 종류
DEFAULT_EXT = {"video": "mp4", "audio": "mp3", "photo": "png"}

_ROT = [("0", "없음"), ("90", "90°"), ("180", "180°"), ("270", "270°")]
_FLIP = [("none", "없음"), ("h", "좌우"), ("v", "상하")]
_RATIO = [("none", "없음"), ("1:1", "1:1"), ("4:3", "4:3"), ("16:9", "16:9"), ("custom", "직접 입력")]
_AUDIO_FILTER = "오디오 (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma);;모든 파일 (*.*)"
_SUB_FILTER = "자막 (*.srt *.ass *.ssa *.vtt);;모든 파일 (*.*)"
_IMG_FILTER = "이미지 (*.png *.jpg *.jpeg *.webp *.bmp);;모든 파일 (*.*)"

TOOLS: dict[str, list[Tool]] = {
    "video": [
        Tool("v_trim", "video", "자르기", "scissors", "자르기 시작", "cut", [
            Field("range", "time2"),
            Field("fast", "check", "재인코딩 없이 빠르게 자르기 (구간이 조금 어긋날 수 있어요)", default=False),
        ]),
        Tool("v_merge", "video", "합치기", "stack", "합쳐서 저장", "merged", [
            Field("order", "files", "합칠 순서"),
            Field("n1", "note", "끌어서 순서를 바꿀 수 있어요. 해상도는 첫 번째 영상에 맞춰집니다."),
        ], multi=True),
        Tool("v_transform", "video", "크기/회전", "aspect", "적용", "edit", [
            Field("res", "seg", "해상도", [("orig", "원본"), ("1080", "1080p"), ("720", "720p"), ("480", "480p")], "orig"),
            Field("rotate", "seg", "회전", _ROT, "0"),
            Field("flip", "seg", "뒤집기", _FLIP, "none"),
            Field("ratio", "seg", "크롭", _RATIO, "none"),
            Field("crop", "crop", show_if=("ratio", "custom")),
        ]),
        Tool("v_speed", "video", "속도/FPS", "gauge", "적용", "speed", [
            Field("speed", "seg", "속도", [("0.5", "0.5배"), ("1", "1배"), ("2", "2배"), ("4", "4배")], "1"),
            Field("fps", "seg", "FPS", [("orig", "원본"), ("24", "24"), ("30", "30"), ("60", "60")], "orig"),
        ]),
        Tool("v_audio", "video", "소리", "volume", "적용", "audio", [
            Field("mode", "seg", "소리", [("keep", "그대로"), ("remove", "제거"), ("replace", "다른 음원으로 교체")], "keep"),
            Field("volume", "slider", "볼륨", default=100, min=0, max=200, unit="%", show_if=("mode", ("keep", "replace"))),
            Field("audio_file", "pick", "교체할 음원", pick_title="음원 선택", pick_filter=_AUDIO_FILTER,
                  show_if=("mode", "replace")),
        ]),
        Tool("v_subs", "video", "자막", "subtitles", "적용", "sub", [
            Field("mode", "seg", "자막", [("burn", "영상에 입히기"), ("track", "자막 트랙으로 넣기"), ("remove", "자막 빼기")], "burn"),
            Field("sub_file", "pick", "자막 파일", pick_title="자막 선택", pick_filter=_SUB_FILTER,
                  show_if=("mode", ("burn", "track"))),
        ]),
    ],
    "audio": [
        Tool("a_trim", "audio", "자르기", "scissors", "자르기 시작", "cut", [
            Field("range", "time2"),
            Field("fade", "seg", "페이드", [("none", "없음"), ("in", "시작"), ("out", "끝"), ("both", "양쪽")], "none"),
        ]),
        Tool("a_merge", "audio", "합치기", "stack", "합쳐서 저장", "merged", [
            Field("order", "files", "합칠 순서"),
            Field("mode", "seg", "곡 사이", [("none", "바로 이어붙이기"), ("gap", "1초 간격"), ("cross", "크로스페이드")], "none"),
        ], multi=True),
        Tool("a_volume", "audio", "볼륨", "volume", "적용", "vol", [
            Field("volume", "slider", "볼륨", default=120, min=0, max=300, unit="%"),
            Field("norm", "seg", "자동", [("off", "끔"), ("on", "볼륨 평준화")], "off"),
        ]),
        Tool("a_speed", "audio", "속도", "gauge", "적용", "speed", [
            Field("speed", "seg", "속도", [("0.5", "0.5배"), ("0.75", "0.75배"), ("1", "1배"), ("1.25", "1.25배"),
                                          ("1.5", "1.5배"), ("2", "2배")], "1.25"),
            Field("pitch", "seg", "음높이", [("keep", "유지"), ("change", "같이 변함")], "keep"),
        ]),
    ],
    "photo": [
        Tool("p_resize", "photo", "크기", "aspect", "적용", "resized", [
            Field("quick", "seg", "크기", [("custom", "직접 입력"), ("orig", "원본"), ("50", "50%"),
                                          ("1920", "긴 변 1920"), ("1280", "긴 변 1280")], "1920"),
            Field("size", "size", show_if=("quick", "custom")),
            Field("keep", "seg", "비율", [("keep", "고정"), ("free", "자유")], "keep", show_if=("quick", "custom")),
        ]),
        Tool("p_rotate", "photo", "회전/뒤집기", "rotate", "적용", "rotated", [
            Field("rotate", "seg", "회전", _ROT, "90"),
            Field("flip", "seg", "뒤집기", _FLIP, "none"),
        ]),
        Tool("p_crop", "photo", "크롭", "crop", "적용", "crop", [
            Field("ratio", "seg", "비율", _RATIO[1:], "1:1"),
            Field("crop", "crop", show_if=("ratio", "custom")),
        ]),
        Tool("p_mark", "photo", "워터마크", "drop", "적용", "mark", [
            Field("logo", "pick", "로고 이미지", pick_title="로고 선택", pick_filter=_IMG_FILTER),
            Field("pos", "pos9", "위치", default=8),
            Field("opacity", "slider", "투명도", default=60, min=10, max=100, unit="%"),
            Field("size", "seg", "크기", [("10", "10%"), ("20", "20%"), ("30", "30%"), ("50", "50%")], "20"),
        ]),
    ],
    "convert": [
        Tool("convert", "convert", "형식 변환", "swap", "변환 시작", "converted", [Field("target", "format")]),
    ],
}


def tool_by_id(tool_id: str) -> Tool:
    for tools in TOOLS.values():
        for t in tools:
            if t.id == tool_id:
                return t
    raise KeyError(tool_id)


def defaults(tool: Tool) -> dict:
    """화면을 열었을 때의 기본 옵션 값."""
    p: dict[str, Any] = {}
    for f in tool.fields:
        if f.kind in ("seg", "slider", "check", "pos9"):
            p[f.key] = f.default
        elif f.kind == "pick":
            p[f.key] = ""
        elif f.kind == "time2":
            p.update(start="", end="")
        elif f.kind == "size":
            p.update(w="", h="")
        elif f.kind == "crop":
            p.update(cw="", ch="", cx="0", cy="0")
        elif f.kind == "format":
            p["target"] = ""
    return p


def visible(f: Field, p: dict) -> bool:
    if f.show_if is None:
        return True
    key, val = f.show_if
    cur = p.get(key)
    return cur in val if isinstance(val, tuple) else cur == val


# ===================================================================== 공용
def parse_time(text: str) -> float | None:
    """'1:02:03.5', '02:03', '90' -> 초. 비어 있으면 None."""
    text = (text or "").strip()
    if not text:
        return None
    parts = text.split(":")
    try:
        if len(parts) > 3:
            raise ValueError
        total = 0.0
        for part in parts:
            total = total * 60 + float(part)
    except ValueError:
        raise ToolError(tr("시간 형식을 확인해 주세요. 예: 90, 1:30, 0:01:30")) from None
    if total < 0:
        raise ToolError(tr("시간 형식을 확인해 주세요. 예: 90, 1:30, 0:01:30"))
    return total


def _int(text: str, name: str = "") -> int | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        v = int(float(text))
    except ValueError:
        raise ToolError(tr("숫자로 입력해 주세요.")) from None
    if v < 0:
        raise ToolError(tr("숫자로 입력해 주세요."))
    return v


_BASE = ["-hide_banner", "-nostdin", "-n", "-progress", "pipe:1", "-nostats"]


def _unique(folder: Path, stem: str, ext: str) -> Path:
    out = folder / f"{stem}.{ext}"
    i = 1
    while out.exists():
        out = folder / f"{stem}_{i}.{ext}"
        i += 1
    return out


def output_path(src: str, suffix: str, ext: str, out_dir: str | None = None) -> Path:
    """원본 이름 + _접미사.확장자 (원본 폴더 또는 지정 폴더). 겹치면 번호를 붙인다."""
    s = Path(src)
    return _unique(Path(out_dir) if out_dir else s.parent, f"{s.stem}_{suffix}", ext)


def resolve_ext(module: str, src: str, out_ext: str) -> str:
    """저장 형식: 직접 고른 것 > 원본과 같은 형식(가능하면) > 모듈 기본값."""
    if out_ext:
        return out_ext
    e = simple.ext_of(src)
    return e if e in MODULE_EXTS[module] else DEFAULT_EXT[module]


def module_of(item: dict) -> str:
    """파일 종류에 맞는 도구 묶음 (동영상은 동영상 도구, 음악은 음악 도구, 사진은 사진 도구)."""
    return KIND_MODULE[item["kind"]]


def accepts(module: str, item: dict) -> bool:
    if module == "video":
        return item["kind"] == "video"
    if module == "audio":
        return item["kind"] in ("audio", "video")
    return item["kind"] == "image" or simple.ext_of(item["path"]) == "gif"


def _even(n: float) -> int:
    return max(2, int(n) // 2 * 2)


def _req_pick(p: dict, key: str, msg: str) -> str:
    path = (p.get(key) or "").strip()
    if not path or not Path(path).is_file():
        raise ToolError(tr(msg))
    return path


def _atempo(s: float) -> str:
    """atempo 는 0.5~2.0 만 받으므로 필요하면 여러 번 이어 붙인다."""
    parts = []
    while s > 2.0:
        parts.append("atempo=2.0")
        s /= 2.0
    while s < 0.5:
        parts.append("atempo=0.5")
        s /= 0.5
    parts.append(f"atempo={s:.4f}")
    return ",".join(parts)


def _clip(p: dict, info) -> tuple[float | None, float | None, float | None]:
    """(시작, 끝, 결과 길이). 자르기 입력 검증 포함."""
    start, end = parse_time(p.get("start", "")), parse_time(p.get("end", ""))
    if start is not None and end is not None and end <= start:
        raise ToolError(tr("끝 시간은 시작 시간보다 커야 합니다."))
    if end is not None:
        dur = end - (start or 0.0)
    elif info.duration is not None:
        dur = max(info.duration - (start or 0.0), 0.0)
    else:
        dur = None
    return start, end, dur


# ===================================================================== 영상 공용
def _vspec(ext: str):
    return simple.VIDEO_SPECS[ext]          # (v_ok, a_ok, v_enc, a_enc, extra)


def _vmap(ext: str) -> list[str]:
    return ["-map", "0:v:0?", "-map", "0:a?" if ext in simple._MULTI_AUDIO else "0:a:0?", "-sn", "-map_metadata", "0"]


def _vcodec(ext: str, info, force: bool = False) -> list[str]:
    v_ok, _a, v_enc, _ae, _x = _vspec(ext)
    if not force and simple._can_copy(info.vcodec, v_ok):
        return ["-c:v", "copy"]
    return list(v_enc)


def _acodec(ext: str, info, force: bool = False) -> list[str]:
    _v, a_ok, _ve, a_enc, _x = _vspec(ext)
    if info.acodec is None:
        return ["-an"]
    if not force and simple._can_copy(info.acodec, a_ok):
        return ["-c:a", "copy"]
    return list(a_enc)


# ===================================================================== 동영상
def _v_trim(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    start, end, dur = _clip(p, info)
    if start is None and end is None:
        raise ToolError(tr("시작이나 끝 시간을 입력해 주세요."))
    args = [ff, *_BASE]
    if start:
        args += ["-ss", f"{start:g}"]
    args += ["-i", it["path"]]
    if end is not None:
        args += ["-t", f"{dur:g}"]
    v_ok, a_ok, v_enc, a_enc, extra = _vspec(ext)
    can_copy = simple._can_copy(info.vcodec, v_ok) and (info.acodec is None or simple._can_copy(info.acodec, a_ok))
    if p.get("fast") and can_copy:
        args += ["-map", "0:v:0?", "-map", "0:a?", "-c", "copy", "-avoid_negative_ts", "make_zero", "-sn"]
    else:
        args += _vmap(ext) + _vcodec(ext, info, force=True) + _acodec(ext, info, force=True)
    return args + extra + [out], dur


def _v_merge(ff, items, p, ext, out):
    if len(items) < 2:
        raise ToolError(tr("합치려면 파일이 2개 이상 필요합니다."))
    first = items[0]["info"]
    w, h = _even(first.width or 1280), _even(first.height or 720)
    fps = f"{first.fps:.3f}" if first.fps else "30"
    args = [ff, *_BASE]
    graph, joined, total = [], "", 0.0
    for i, it in enumerate(items):
        args += ["-i", it["path"]]
        inf = it["info"]
        d = inf.duration or 1.0
        total += d
        graph.append(f"[{i}:v:0]scale={w}:{h}:force_original_aspect_ratio=decrease,"
                     f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},format=yuv420p[v{i}]")
        if inf.acodec:
            graph.append(f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
        else:  # 소리가 없는 영상은 같은 길이의 무음으로 채운다
            graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={d:.3f}[a{i}]")
        joined += f"[v{i}][a{i}]"
    graph.append(f"{joined}concat=n={len(items)}:v=1:a=1[v][a]")
    _v_ok, _a_ok, v_enc, a_enc, extra = _vspec(ext)
    args += ["-filter_complex", ";".join(graph), "-map", "[v]", "-map", "[a]", "-map_metadata", "0",
             *v_enc, *a_enc, *extra, out]
    return args, total


def _crop_filter(ratio: str, p: dict) -> str | None:
    if ratio in ("", "none"):
        return None
    if ratio == "custom":
        cw, ch = _int(p.get("cw", "")), _int(p.get("ch", ""))
        if not cw or not ch:
            raise ToolError(tr("크롭 영역(가로, 세로)을 입력해 주세요."))
        return f"crop={cw}:{ch}:{_int(p.get('cx', '0')) or 0}:{_int(p.get('cy', '0')) or 0}"
    a, b = (float(x) for x in ratio.split(":"))
    r = a / b
    return f"crop='trunc(min(iw,ih*{r:.5f})/2)*2':'trunc(min(ih,iw/{r:.5f})/2)*2'"


def _rotate_flip(p: dict) -> list[str]:
    f = []
    rot = p.get("rotate", "0")
    if rot == "90":
        f.append("transpose=1")
    elif rot == "180":
        f.append("transpose=1,transpose=1")
    elif rot == "270":
        f.append("transpose=2")
    flip = p.get("flip", "none")
    if flip == "h":
        f.append("hflip")
    elif flip == "v":
        f.append("vflip")
    return f


def _v_transform(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    f = []
    c = _crop_filter(p.get("ratio", "none"), p)
    if c:
        f.append(c)
    f += _rotate_flip(p)
    if p.get("res", "orig") != "orig":
        f.append(f"scale=-2:{int(p['res'])}")
    if not f:
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    args = [ff, *_BASE, "-i", it["path"], *_vmap(ext), "-vf", ",".join(f)]
    args += _vcodec(ext, info, force=True) + _acodec(ext, info) + _vspec(ext)[4]
    return args + [out], info.duration


def _v_speed(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    s = float(p.get("speed", "1"))
    fps = p.get("fps", "orig")
    if s == 1 and fps == "orig":
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    vf = []
    if s != 1:
        vf.append(f"setpts=PTS/{s:g}")
    if fps != "orig":
        vf.append(f"fps={int(fps)}")
    args = [ff, *_BASE, "-i", it["path"], *_vmap(ext), "-vf", ",".join(vf)]
    if s != 1 and info.acodec:
        args += ["-af", _atempo(s)] + _acodec(ext, info, force=True)
    else:
        args += _acodec(ext, info)
    args += _vcodec(ext, info, force=True) + _vspec(ext)[4]
    return args + [out], (info.duration / s if info.duration else None)


def _v_audio(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    mode = p.get("mode", "keep")
    vol = int(p.get("volume", 100))
    extra = _vspec(ext)[4]
    a_enc = list(_vspec(ext)[3])
    af = ["-af", f"volume={vol / 100:.3f}"] if vol != 100 else []
    if mode == "remove":
        args = [ff, *_BASE, "-i", it["path"], "-map", "0:v:0?", "-sn", "-map_metadata", "0", "-an",
                *_vcodec(ext, info)]
    elif mode == "replace":
        audio = _req_pick(p, "audio_file", "교체할 음원 파일을 선택해 주세요.")
        args = [ff, *_BASE, "-i", it["path"], "-i", audio, "-map", "0:v:0", "-map", "1:a:0", "-shortest",
                "-map_metadata", "0", *_vcodec(ext, info), *af, *a_enc]
    else:
        if vol == 100:
            raise ToolError(tr("바꿀 항목을 선택해 주세요."))
        if not info.acodec:
            raise ToolError(tr("이 영상에는 소리가 없어요."))
        args = [ff, *_BASE, "-i", it["path"], *_vmap(ext), *_vcodec(ext, info), *af, *a_enc]
    return args + extra + [out], info.duration


def _esc_filter_path(path: str) -> str:
    """subtitles 필터용 경로: 역슬래시는 /로, ':'와 '는 이스케이프."""
    return path.replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


_SUB_CODEC = {"mp4": "mov_text", "m4v": "mov_text", "mov": "mov_text", "3gp": "mov_text", "3g2": "mov_text",
              "mkv": "srt", "webm": "webvtt"}


def _v_subs(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    mode = p.get("mode", "burn")
    extra = _vspec(ext)[4]
    if mode == "remove":
        args = [ff, *_BASE, "-i", it["path"], "-map", "0:v:0?", "-map", "0:a?", "-sn", "-map_metadata", "0",
                *_vcodec(ext, info), *_acodec(ext, info)]
    elif mode == "track":
        sub = _req_pick(p, "sub_file", "자막 파일을 선택해 주세요.")
        codec = _SUB_CODEC.get(ext)
        if not codec:
            raise ToolError(tr("이 형식은 자막 트랙을 지원하지 않아요. MP4, MKV, MOV, WebM을 선택해 주세요."))
        args = [ff, *_BASE, "-i", it["path"], "-i", sub, "-map", "0:v:0?", "-map", "0:a?", "-map", "1:0",
                "-map_metadata", "0", *_vcodec(ext, info), *_acodec(ext, info), "-c:s", codec]
    else:
        sub = _req_pick(p, "sub_file", "자막 파일을 선택해 주세요.")
        args = [ff, *_BASE, "-i", it["path"], *_vmap(ext), "-vf", f"subtitles='{_esc_filter_path(sub)}'",
                *_vcodec(ext, info, force=True), *_acodec(ext, info)]
    return args + extra + [out], info.duration


# ===================================================================== 음악
def _aout(ext: str, info, force: bool = False) -> list[str]:
    copy_ok, enc, extra = simple.AUDIO_SPECS[ext]
    if not force and simple._can_copy(info.acodec, copy_ok):
        return ["-c:a", "copy", *extra]
    return [*enc, *extra]


def _a_trim(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    start, end, dur = _clip(p, info)
    fade = p.get("fade", "none")
    if start is None and end is None and fade == "none":
        raise ToolError(tr("시작이나 끝 시간을 입력해 주세요."))
    args = [ff, *_BASE]
    if start:
        args += ["-ss", f"{start:g}"]
    args += ["-i", it["path"]]
    if end is not None:
        args += ["-t", f"{dur:g}"]
    args += ["-vn", "-map", "0:a:0", "-map_metadata", "0"]
    af = []
    if fade in ("in", "both"):
        af.append("afade=t=in:st=0:d=1")
    if fade in ("out", "both"):
        if dur is None or dur < 2:
            raise ToolError(tr("페이드를 쓰려면 구간이 2초 이상이어야 합니다."))
        af.append(f"afade=t=out:st={dur - 1:.3f}:d=1")
    if af:
        args += ["-af", ",".join(af)]
    return args + _aout(ext, info, force=bool(af)) + [out], dur


def _a_merge(ff, items, p, ext, out):
    if len(items) < 2:
        raise ToolError(tr("합치려면 파일이 2개 이상 필요합니다."))
    args = [ff, *_BASE]
    graph = []
    for i, it in enumerate(items):
        args += ["-i", it["path"]]
        graph.append(f"[{i}:a:0]aresample=48000,aformat=channel_layouts=stereo[a{i}]")
    mode = p.get("mode", "none")
    n = len(items)
    total = sum((it["info"].duration or 0) for it in items)
    if mode == "cross":
        cur = "a0"
        for i in range(1, n):
            graph.append(f"[{cur}][a{i}]acrossfade=d=2:c1=tri:c2=tri[x{i}]")
            cur = f"x{i}"
        label = cur
        total = max(total - 2 * (n - 1), 1)
    else:
        seq = ""
        for i in range(n):
            seq += f"[a{i}]"
            if mode == "gap" and i < n - 1:
                graph.append(f"anullsrc=r=48000:cl=stereo,atrim=duration=1[s{i}]")
                seq += f"[s{i}]"
        count = n + (n - 1 if mode == "gap" else 0)
        graph.append(f"{seq}concat=n={count}:v=0:a=1[out]")
        label = "out"
        if mode == "gap":
            total += n - 1
    args += ["-filter_complex", ";".join(graph), "-map", f"[{label}]", "-map_metadata", "0",
             *_aout(ext, items[0]["info"], force=True), out]
    return args, total


def _a_volume(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    vol = int(p.get("volume", 100))
    af = []
    if vol != 100:
        af.append(f"volume={vol / 100:.3f}")
    if p.get("norm") == "on":
        af.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    if not af:
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    args = [ff, *_BASE, "-i", it["path"], "-vn", "-map", "0:a:0", "-map_metadata", "0", "-af", ",".join(af)]
    return args + _aout(ext, info, force=True) + [out], info.duration


def _a_speed(ff, items, p, ext, out):
    it = items[0]
    info = it["info"]
    s = float(p.get("speed", "1"))
    if s == 1:
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    if p.get("pitch") == "change":
        sr = info.sample_rate or 44100
        af = f"asetrate={int(sr * s)},aresample={sr}"
    else:
        af = _atempo(s)
    args = [ff, *_BASE, "-i", it["path"], "-vn", "-map", "0:a:0", "-map_metadata", "0", "-af", af]
    return args + _aout(ext, info, force=True) + [out], (info.duration / s if info.duration else None)


# ===================================================================== 사진
_FLATTEN_CORE = ("split=2[bg][fg];[bg]drawbox=c=white@1:replace=1:t=fill[bg2];"
                 "[bg2][fg]overlay=format=auto,format=rgb24")


def _image_cmd(ff, inputs: list[str], body: str, label: str, ext: str, out: str) -> list[str]:
    """body 가 [label] 을 만들어 내는 필터 그래프. 형식에 따라 마무리 필터를 붙인다."""
    graph, final = body, label
    if ext in ("jpg", "jpeg"):                      # 투명 배경은 흰색으로
        graph += f";[{label}]{_FLATTEN_CORE}[out]"
        final = "out"
    elif ext == "gif":
        graph += f";[{label}]{simple._GIF_PALETTE}[out]"
        final = "out"
    elif ext == "ico":
        graph += f";[{label}]{simple._ICO_SCALE}[out]"
        final = "out"
    args = [ff, *_BASE]
    for i in inputs:
        args += ["-i", i]
    return args + ["-filter_complex", graph, "-map", f"[{final}]", "-frames:v", "1", "-update", "1",
                   *simple.image_codec_opts(ext), out]


def _p_resize(ff, items, p, ext, out):
    it = items[0]
    quick = p.get("quick", "custom")
    if quick == "orig":
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    if quick == "50":
        f = "scale=trunc(iw/2):trunc(ih/2):flags=lanczos"
    elif quick in ("1920", "1280"):
        n = int(quick)
        f = f"scale=w='if(gt(iw,ih),min({n},iw),-1)':h='if(gt(iw,ih),-1,min({n},ih))':flags=lanczos"
    else:
        w, h = _int(p.get("w", "")), _int(p.get("h", ""))
        if not w and not h:
            raise ToolError(tr("크기를 입력해 주세요."))
        if w and h:
            f = (f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos" if p.get("keep") == "keep"
                 else f"scale={w}:{h}:flags=lanczos")
        else:
            f = f"scale={w or -1}:{h or -1}:flags=lanczos"
    return _image_cmd(ff, [it["path"]], f"[0:v]{f}[t]", "t", ext, out), None


def _p_rotate(ff, items, p, ext, out):
    f = _rotate_flip(p)
    if not f:
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    return _image_cmd(ff, [items[0]["path"]], f"[0:v]{','.join(f)}[t]", "t", ext, out), None


def _p_crop(ff, items, p, ext, out):
    c = _crop_filter(p.get("ratio", "none"), p)
    if not c:
        raise ToolError(tr("바꿀 항목을 선택해 주세요."))
    return _image_cmd(ff, [items[0]["path"]], f"[0:v]{c}[t]", "t", ext, out), None


def _p_mark(ff, items, p, ext, out):
    it = items[0]
    logo = _req_pick(p, "logo", "로고 이미지를 선택해 주세요.")
    pct = int(p.get("size", "20"))
    px = max(8, int((it["info"].width or 1000) * pct / 100))
    op = max(10, min(100, int(p.get("opacity", 60)))) / 100
    pos = int(p.get("pos", 8))
    col, row = pos % 3, pos // 3
    x = ["20", "(main_w-overlay_w)/2", "main_w-overlay_w-20"][col]
    y = ["20", "(main_h-overlay_h)/2", "main_h-overlay_h-20"][row]
    body = (f"[1:v]scale={px}:-1,format=rgba,colorchannelmixer=aa={op:.2f}[wm];"
            f"[0:v][wm]overlay={x}:{y}[t]")
    return _image_cmd(ff, [it["path"], logo], body, "t", ext, out), None


# ===================================================================== 형식 변환
def _convert(ff, items, p, ext, out):
    it = items[0]
    target = (p.get("target") or "").strip()
    if not target:
        raise ToolError(tr("바꿀 형식을 골라 주세요."))
    src_ext = simple.ext_of(it["path"])
    if src_ext == target:
        raise ToolError(tr("이미 같은 형식이에요"))
    if not simple.can_convert(it["kind"], src_ext, target):
        raise ToolError(tr("이 형식으로는 바꿀 수 없어요"))
    return simple.build_args(ff, it["path"], out, target, it["info"], it["kind"], "original"), it["info"].duration


_BUILDERS = {
    "convert": _convert,
    "v_trim": _v_trim, "v_merge": _v_merge, "v_transform": _v_transform, "v_speed": _v_speed,
    "v_audio": _v_audio, "v_subs": _v_subs,
    "a_trim": _a_trim, "a_merge": _a_merge, "a_volume": _a_volume, "a_speed": _a_speed,
    "p_resize": _p_resize, "p_rotate": _p_rotate, "p_crop": _p_crop, "p_mark": _p_mark,
}


# ===================================================================== 실행 계획
# 여러 도구를 한 번에 고르면 아래 순서로 이어서 실행한다 (앞 단계 결과가 다음 단계의 입력).
#  - 합치기가 맨 앞 (그 뒤의 자르기 시간 등은 합친 결과 기준)
#  - 영상에 입히는 자막은 원본 시간 기준이라 자르기/속도보다 먼저, 트랙 자막은 다른 단계가 지워 버리므로 맨 마지막
#  - 사진은 크롭 좌표가 원본 기준이라 크롭이 먼저, 워터마크는 최종 크기 기준이라 맨 마지막
#  - 형식 변환은 모든 편집이 끝난 뒤
_RANK = {
    "v_merge": 0, "v_trim": 2, "v_transform": 3, "v_speed": 4, "v_audio": 5,
    "a_merge": 0, "a_trim": 1, "a_volume": 2, "a_speed": 3,
    "p_crop": 0, "p_rotate": 1, "p_resize": 2, "p_mark": 3,
    "convert": 99,
}
# 단계 사이에 넘기는 임시 파일 형식 (무손실에 가깝게)
INTERMEDIATE_EXT = {"video": "mkv", "audio": "flac", "photo": "png"}


def step_rank(tool: Tool, params: dict) -> int:
    if tool.id == "v_subs":
        return 1 if params.get("mode", "burn") == "burn" else 6
    return _RANK[tool.id]


def order_steps(steps: list[tuple[Tool, dict]]) -> list[tuple[Tool, dict]]:
    return sorted(steps, key=lambda s: step_rank(*s))


def _virtual_item(group: list[dict], merged: bool, ext: str | None) -> dict:
    """뒷 단계를 미리 검사할 때 쓰는 가상의 입력: 앞 단계가 만들 임시 파일처럼 보이게 한다."""
    first = group[0]
    info = first["info"]
    if merged:
        total = sum((i["info"].duration or 0.0) for i in group)
        info = replace(info, duration=total or None)
    path = f"virtual.{ext}" if ext else first["path"]
    return {**first, "path": path, "info": info}


def _prepare_step(prev: Plan, build, ffmpeg: str, ffprobe: str, params: dict, ext: str, quality: str):
    def prepare(plan: Plan) -> None:
        if not Path(prev.output).is_file():
            raise ToolError(tr("앞 단계가 끝나지 않았어요."))
        info = _probe(ffprobe, prev.output)
        item = {"path": prev.output, "info": info, "kind": simple.kind_of(prev.output, info)}
        args, dur = build(ffmpeg, [item], params, ext, plan.output)
        plan.args, plan.duration = simple._tune(args, quality), dur
    return prepare


def _probe(ffprobe: str, path: str):
    from .probe import probe          # 늦게 불러온다 (probe 는 단계 실행 때만 필요)
    return probe(ffprobe, path)


def plan_chain(steps: list[tuple[Tool, dict]], ffmpeg: str, items: list[dict], out_ext: str = "",
               quality: str = "original", out_dir: str | None = None, tmp_dir: str | None = None,
               ffprobe: str | None = None) -> list[Plan]:
    """같은 종류의 파일들에 고른 도구들을 정해진 순서로 이어 붙인 실행 계획 (파일마다 단계 수만큼 Plan).
    steps 맨 끝에는 형식 변환(convert)이 올 수 있다. 입력 오류는 모든 단계를 미리 검사해서 ToolError 로 알린다.
    두 단계 이상이면 임시 파일을 tmp_dir 에 두고 ffprobe 로 앞 단계 결과를 읽어 다음 명령을 만든다."""
    if not items:
        raise ToolError(tr("파일을 먼저 넣어 주세요."))
    if not steps:
        raise ToolError(tr("적용할 도구를 체크해 주세요."))
    steps = order_steps(steps)
    conv = steps[-1] if steps[-1][0].id == "convert" else None
    edits = steps[:-1] if conv else steps
    module = edits[0][0].module if edits else None
    if len(steps) > 1 and not (tmp_dir and ffprobe):
        raise ValueError("tmp_dir and ffprobe are required for chained tools")
    if module:
        bad = [Path(i["path"]).name for i in items if not accepts(module, i)]
        if bad:
            raise ToolError(tr("이 도구로 다룰 수 없는 파일이 있어요: {names}", names=", ".join(bad)))
    merged = bool(edits) and edits[0][0].multi
    groups = [items] if merged else [[i] for i in items]
    n = len(steps)
    suffix = steps[0][0].suffix if n == 1 else "edit"
    inter = INTERMEDIATE_EXT[module] if module else None
    plans: list[Plan] = []
    for gi, g in enumerate(groups):
        if conv:
            final_ext = (conv[1].get("target") or "").strip()
        else:
            final_ext = resolve_ext(module, g[0]["path"], out_ext)
            if final_ext not in MODULE_EXTS[module]:
                raise ToolError(tr("이 형식은 사용할 수 없어요."))
        virt = _virtual_item(g, merged, inter)
        prev: Plan | None = None
        for si, (tool, params) in enumerate(steps):
            last = si == n - 1
            ext = final_ext if last else inter
            q = quality if last else "original"
            if not last:
                out = Path(tmp_dir) / f"g{gi}_s{si}.{ext}"
            elif n == 1 and conv:
                out = simple.output_path(g[0]["path"], ext, out_dir)       # 형식만 바꿀 때는 원래 이름 그대로
            else:
                out = output_path(g[0]["path"], suffix, ext, out_dir)
            build = _BUILDERS[tool.id]
            args, dur = build(ffmpeg, g if si == 0 else [virt], params, ext, str(out))   # 뒷 단계는 검사용
            plan = Plan(simple._tune(args, q) if si == 0 else [], str(out), dur, g[0],
                        final=last, group=gi, step=si, steps=n, label=tool.name)
            if si > 0:
                plan.prepare = _prepare_step(prev, build, ffmpeg, ffprobe, params, ext, q)
            plans.append(plan)
            prev = plan
    return plans


def plan_jobs(tool: Tool, ffmpeg: str, items: list[dict], params: dict, out_ext: str = "",
              quality: str = "original", out_dir: str | None = None) -> list[Plan]:
    """도구 하나만 쓰는 실행 계획 (plan_chain 의 단일 단계 버전)."""
    return plan_chain([(tool, params)], ffmpeg, items, out_ext, quality, out_dir)


def plan_all(steps: list[tuple[Tool, dict]], ffmpeg: str, items: list[dict], quality: str = "original",
             out_dir: str | None = None, tmp_dir: str | None = None,
             ffprobe: str | None = None) -> tuple[list[Plan], list[tuple[str, str]]]:
    """여러 종류의 파일을 한꺼번에: 파일은 종류별로(동영상/음악/사진) 그 종류의 체크한 도구만 적용받고,
    형식 변환을 체크했으면 마지막에 바꿀 수 있는 파일에만 적용된다.
    돌려주는 값: (실행 계획들, [(파일 이름, 건너뛴 이유)])."""
    if not items:
        raise ToolError(tr("파일을 먼저 넣어 주세요."))
    if not steps:
        raise ToolError(tr("적용할 도구를 체크해 주세요."))
    conv = next((s for s in steps if s[0].id == "convert"), None)
    target = (conv[1].get("target") or "").strip() if conv else ""
    if conv and not target:
        raise ToolError(tr("바꿀 형식을 골라 주세요."))
    by_module: dict[str, list[dict]] = {}
    for it in items:
        by_module.setdefault(module_of(it), []).append(it)
    plans: list[Plan] = []
    notes: list[tuple[str, str]] = []
    part, groups_done = 0, 0
    for module in ("video", "audio", "photo"):
        files = by_module.get(module, [])
        edits = order_steps([s for s in steps if s[0].module == module])
        if not files:
            continue
        if not edits and not conv:
            notes += [(Path(f["path"]).name, tr("이 파일에 적용할 도구가 선택되지 않았어요")) for f in files]
            continue
        groups = [files] if edits and edits[0][0].multi else [[f] for f in files]
        for g in groups:
            src = g[0]
            name = Path(src["path"]).name
            use, out_ext = list(edits), ""
            if target:
                if edits:
                    if target in MODULE_EXTS[module]:
                        out_ext = target                                   # 마지막 편집이 바로 그 형식으로 저장
                    elif simple.can_convert(src["kind"], "", target):
                        use.append(conv)                                   # 종류가 바뀌는 변환은 마지막 단계로
                    else:
                        notes.append((name, tr("이 형식으로는 바꿀 수 없어요")))
                elif simple.ext_of(src["path"]) == target:
                    notes.append((name, tr("이미 같은 형식이에요")))
                    continue
                elif simple.can_convert(src["kind"], simple.ext_of(src["path"]), target):
                    use = [conv]
                else:
                    notes.append((name, tr("이 형식으로는 바꿀 수 없어요")))
                    continue
            sub = None
            if len(use) > 1:
                sub = str(Path(tmp_dir) / f"p{part}")
                Path(sub).mkdir(parents=True, exist_ok=True)
                part += 1
            built = plan_chain(use, ffmpeg, g, out_ext, quality, out_dir, sub, ffprobe)
            for pl in built:                       # plan_chain 은 한 번에 결과 하나(group 0)를 만든다
                pl.group = groups_done
            groups_done += 1
            plans += built
    if not plans:
        raise ToolError(notes[0][1] if notes else tr("선택한 도구를 적용할 수 있는 파일이 없어요."))
    return plans, notes
