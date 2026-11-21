"""간단한 다국어(한국어/영어). 한국어 원문을 키로 쓰고, 영어일 때만 번역을 찾는다.

사용:  tr("파일 추가")  /  tr("{n}개 변환 완료", n=3)
번역이 없으면 한국어 원문이 그대로 나오고, tests/test_i18n.py 가 누락을 잡아낸다.
"""
from __future__ import annotations

from PySide6.QtCore import QLocale

LANGUAGES = ("ko", "en")
_lang = "ko"


def set_language(code: str) -> None:
    global _lang
    _lang = code if code in LANGUAGES else "ko"


def language() -> str:
    return _lang


def resolve(setting: str | None) -> str:
    """설정값('auto'/'ko'/'en')을 실제 언어로. auto 는 Windows 표시 언어를 따른다."""
    if setting in LANGUAGES:
        return setting
    return "ko" if QLocale.system().name().lower().startswith("ko") else "en"


def tr(text: str, **kw) -> str:
    out = EN.get(text, text) if _lang == "en" else text
    return out.format(**kw) if kw else out


EN: dict[str, str] = {
    # --- 화면 공통 ---
    "여기에 파일을 끌어다 놓거나 눌러서 선택하세요": "Drop files here, or click to choose files",
    "영상": "Video",
    "오디오": "Audio",
    "이미지": "Image",
    "{n}개 형식 지원 · 원본 화질 유지": "{n} formats · Original quality kept",
    "설정": "Settings",
    "처음으로": "Start over",
    "검색  (예: mp3, 영상, 이미지)": "Search  (e.g. mp3, video, image)",
    "파일 추가": "Add files",
    "변환": "Convert",
    "{fmt}(으)로 변환": "Convert to {fmt}",
    "변환 중...": "Converting...",
    "취소": "Cancel",
    "폴더 열기": "Open folder",
    "새로 변환하기": "Convert more",
    "파일 선택": "Choose files",
    "모든 파일 (*.*)": "All files (*.*)",
    "읽을 수 없는 파일: {names}": "Can't read: {names}",
    "{name} 외 {n}개": "{name} and {n} more",
    "저장 위치": "Save location",
    "저장 폴더를 만들 수 없습니다.\n{err}": "Couldn't create the save folder.\n{err}",
    "이미 같은 형식이에요": "Already in this format",
    "이 형식으로는 바꿀 수 없어요": "Can't convert to this format",
    "알림": "Notice",
    "선택한 형식으로 바꿀 수 있는 파일이 없습니다.": "None of the files can be converted to the selected format.",
    "변환 중인 파일": "Converting",
    "취소하는 중...": "Cancelling...",
    "취소되었습니다": "Cancelled",
    "변환에 실패했어요": "Conversion failed",
    "완료!": "Done!",
    "{n}개 변환 완료": "{n} converted",
    " · {n}개 실패/건너뜀": " · {n} failed/skipped",
    "결과 미리보기": "Result preview",
    # --- ffmpeg 경로/설치 ---
    "ffmpeg.exe / ffprobe.exe 가 있는 폴더 선택": "Choose the folder containing ffmpeg.exe and ffprobe.exe",
    "ffmpeg 경로를 설정했습니다.\n{path}": "FFmpeg path set.\n{path}",
    "선택한 폴더에 ffmpeg.exe와 ffprobe.exe가 함께 있어야 합니다.":
        "The folder must contain both ffmpeg.exe and ffprobe.exe.",
    "ffmpeg 설치": "Install FFmpeg",
    "ffmpeg를 다시 설치합니다. ": "FFmpeg will be reinstalled. ",
    "ffmpeg가 없습니다. ": "FFmpeg was not found. ",
    "지금 자동으로 내려받아 앱 폴더의 bin 에 설치할까요?\n\n출처: gyan.dev 릴리스 빌드 (약 100MB, GPL 라이선스)\n"
    "다운로드 후 SHA-256 체크섬을 검증합니다.":
        "Download it now and install it into the app's bin folder?\n\nSource: gyan.dev release build "
        "(about 100 MB, GPL license)\nThe download is verified with its SHA-256 checksum.",
    "준비 중...": "Preparing...",
    "ffmpeg 다운로드 중... {done:.0f} / {total:.0f} MB": "Downloading FFmpeg... {done:.0f} / {total:.0f} MB",
    "설치가 완료되었습니다.": "Installation complete.",
    "ffmpeg 설치 실패": "FFmpeg installation failed",
    "체크섬 확인 중...": "Checking checksum...",
    "ffmpeg 다운로드 중...": "Downloading FFmpeg...",
    "압축 해제 중...": "Extracting...",
    "취소되었습니다.": "Cancelled.",
    "체크섬 정보를 가져오지 못했습니다.": "Couldn't get the checksum.",
    "다운로드 파일의 체크섬이 일치하지 않습니다. (파일 손상 또는 변조 가능성)":
        "The download's checksum does not match (corrupted or tampered file).",
    "압축 파일에서 ffmpeg.exe/ffprobe.exe를 찾지 못했습니다.": "ffmpeg.exe/ffprobe.exe not found in the archive.",
    # --- 변환 실행/결과 ---
    "취소됨": "Cancelled",
    "완료": "Done",
    "실패 (코드 {code})": "Failed (code {code})",
    "ffmpeg 실행에 실패했습니다.": "Couldn't start FFmpeg.",
    "정보 없음": "No info",
    # --- 미리보기 ---
    "불러오는 중…": "Loading…",
    "♪\n오디오": "♪\nAudio",
    ".{ext}\n미리보기 없음": ".{ext}\nNo preview",
    # --- 설정 창 ---
    "원본 파일과 같은 폴더": "Same folder as the original file",
    "지정한 폴더": "A folder I choose",
    "폴더를 선택하세요": "Choose a folder",
    "찾기": "Browse",
    "화질": "Quality",
    "원본 화질 유지": "Keep original quality",
    "가장 선명하고 용량이 큽니다 (기본)": "Sharpest, largest files (default)",
    "균형": "Balanced",
    "화질 차이는 거의 없고 용량이 줄어듭니다": "Hardly any visible difference, smaller files",
    "작은 용량": "Small size",
    "용량을 크게 줄입니다. 화질이 조금 떨어질 수 있습니다": "Much smaller files, slight quality loss possible",
    "변환이 끝나면": "When finished",
    "결과 폴더를 자동으로 열기": "Open the result folder automatically",
    "찾을 수 없음": "Not found",
    "경로 지정": "Set path",
    "다시 설치": "Reinstall",
    "저장": "Save",
    "저장할 폴더 선택": "Choose a save folder",
    "언어": "Language",
    "자동 (시스템 언어)": "Automatic (system language)",
    "언어를 바꾸려면 Swapeg를 다시 시작해야 합니다.\n지금 다시 시작할까요?":
        "Swapeg needs to restart to change the language.\nRestart now?",
}
