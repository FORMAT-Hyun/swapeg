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
    # --- 프로그램 정보 ---
    "정보": "About",
    "프로그램 정보": "About Swapeg",
    "버전": "Version",
    "동영상, 음악, 사진을 변환하고 자르고 합치는 ffmpeg 도구 모음입니다. 화질은 원본 그대로 유지합니다.":
        "Convert, trim, merge and edit your videos, music and photos with FFmpeg. The original quality is kept.",
    "GitHub 저장소": "GitHub repository",
    "새 버전 확인": "Check for new versions",
    "문제 신고 / 의견 보내기": "Report a problem or suggest something",
    "Swapeg는 FFmpeg(gyan.dev의 GPL 빌드)와 Qt for Python(PySide6, LGPL)을 사용합니다. FFmpeg 프로젝트와는 관련이 없습니다.":
        "Swapeg uses FFmpeg (GPL builds from gyan.dev) and Qt for Python (PySide6, LGPL). "
        "It is not affiliated with the FFmpeg project.",
    "닫기": "Close",
    # --- 시작 화면 / 모듈 ---
    "무엇을 할까요? 모듈을 고르거나, 파일을 바로 끌어다 놓으세요.": "What would you like to do? Pick a module, or just drop your files.",
    "형식 변환": "Convert format",
    "동영상": "Video",
    "음악": "Music",
    "사진": "Photo",
    "{n}개 형식으로 바꾸기": "Convert to {n} formats",
    "자르기 · 합치기 · 크기 · 속도 · 소리 · 자막": "Trim · Merge · Size · Speed · Sound · Subtitles",
    "자르기 · 합치기 · 볼륨 · 속도": "Trim · Merge · Volume · Speed",
    "크기 · 회전 · 크롭 · 워터마크": "Resize · Rotate · Crop · Watermark",
    "동영상 파일을 끌어다 놓거나 눌러서 선택하세요": "Drop video files here, or click to choose files",
    "음악 파일을 끌어다 놓거나 눌러서 선택하세요": "Drop music files here, or click to choose files",
    "사진 파일을 끌어다 놓거나 눌러서 선택하세요": "Drop photos here, or click to choose files",
    "이 모듈에서는 다룰 수 없는 파일: {names}": "Can't be used in this module: {names}",
    "계속 편집하기": "Keep editing",
    # --- 도구 화면 ---
    "저장 형식": "Save as",
    "원본과 같은 형식": "Same as original",
    "선택": "Choose",
    "선택 제거": "Remove selected",
    "파일을 선택하세요": "Choose a file",
    "확인해 주세요": "Please check",
    "시작": "Start",
    "가로": "Width",
    "세로": "Height",
    "X": "X",
    "Y": "Y",
    "끝": "End",
    "비워 두면 처음부터 / 끝까지입니다. 예: 90, 1:30, 0:01:30": "Leave empty for the beginning / the end. Examples: 90, 1:30, 0:01:30",
    # --- 도구 이름과 옵션 ---
    "자르기": "Trim",
    "자르기 시작": "Start trimming",
    "합치기": "Merge",
    "합쳐서 저장": "Merge and save",
    "합칠 순서": "Order",
    "끌어서 순서를 바꿀 수 있어요. 해상도는 첫 번째 영상에 맞춰집니다.": "Drag to reorder. The size follows the first video.",
    "크기/회전": "Size / rotate",
    "크기": "Size",
    "회전": "Rotate",
    "회전/뒤집기": "Rotate / flip",
    "뒤집기": "Flip",
    "좌우": "Horizontal",
    "상하": "Vertical",
    "없음": "None",
    "해상도": "Resolution",
    "원본": "Original",
    "크롭": "Crop",
    "직접 입력": "Custom",
    "속도/FPS": "Speed / FPS",
    "속도": "Speed",
    "FPS": "FPS",
    "0.5배": "0.5x", "0.75배": "0.75x", "1배": "1x", "1.25배": "1.25x", "1.5배": "1.5x", "2배": "2x", "4배": "4x",
    "소리": "Sound",
    "그대로": "Keep",
    "제거": "Remove",
    "다른 음원으로 교체": "Replace with another audio",
    "볼륨": "Volume",
    "교체할 음원": "Replacement audio",
    "음원 선택": "Choose audio",
    "자막": "Subtitles",
    "영상에 입히기": "Burn into video",
    "자막 트랙으로 넣기": "Add as subtitle track",
    "자막 빼기": "Remove subtitles",
    "자막 파일": "Subtitle file",
    "자막 선택": "Choose subtitles",
    "재인코딩 없이 빠르게 자르기 (구간이 조금 어긋날 수 있어요)": "Trim fast without re-encoding (may be slightly off)",
    "페이드": "Fade",
    "양쪽": "Both",
    "곡 사이": "Between tracks",
    "바로 이어붙이기": "Join directly",
    "1초 간격": "1 second gap",
    "크로스페이드": "Crossfade",
    "자동": "Auto",
    "끔": "Off",
    "볼륨 평준화": "Normalize loudness",
    "음높이": "Pitch",
    "유지": "Keep",
    "같이 변함": "Changes too",
    "비율": "Ratio",
    "고정": "Locked",
    "자유": "Free",
    "긴 변 1920": "Long side 1920",
    "긴 변 1280": "Long side 1280",
    "워터마크": "Watermark",
    "로고 이미지": "Logo image",
    "로고 선택": "Choose logo",
    "위치": "Position",
    "투명도": "Opacity",
    "적용": "Apply",
    "오디오 (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma);;모든 파일 (*.*)":
        "Audio (*.mp3 *.wav *.flac *.m4a *.aac *.ogg *.opus *.wma);;All files (*.*)",
    "자막 (*.srt *.ass *.ssa *.vtt);;모든 파일 (*.*)": "Subtitles (*.srt *.ass *.ssa *.vtt);;All files (*.*)",
    "이미지 (*.png *.jpg *.jpeg *.webp *.bmp);;모든 파일 (*.*)": "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All files (*.*)",
    # --- 도구 입력 오류 ---
    "시간 형식을 확인해 주세요. 예: 90, 1:30, 0:01:30": "Check the time format. Examples: 90, 1:30, 0:01:30",
    "숫자로 입력해 주세요.": "Enter a number.",
    "끝 시간은 시작 시간보다 커야 합니다.": "The end time must be later than the start time.",
    "시작이나 끝 시간을 입력해 주세요.": "Enter a start or end time.",
    "바꿀 항목을 선택해 주세요.": "Choose what to change.",
    "합치려면 파일이 2개 이상 필요합니다.": "You need at least 2 files to merge.",
    "교체할 음원 파일을 선택해 주세요.": "Choose the replacement audio file.",
    "자막 파일을 선택해 주세요.": "Choose a subtitle file.",
    "로고 이미지를 선택해 주세요.": "Choose a logo image.",
    "이 영상에는 소리가 없어요.": "This video has no sound.",
    "이 형식은 자막 트랙을 지원하지 않아요. MP4, MKV, MOV, WebM을 선택해 주세요.":
        "This format doesn't support subtitle tracks. Choose MP4, MKV, MOV or WebM.",
    "크기를 입력해 주세요.": "Enter a size.",
    "크롭 영역(가로, 세로)을 입력해 주세요.": "Enter the crop area (width and height).",
    "페이드를 쓰려면 구간이 2초 이상이어야 합니다.": "The clip must be at least 2 seconds long to use fades.",
    "파일을 먼저 넣어 주세요.": "Add files first.",
    "이 도구로 다룰 수 없는 파일이 있어요: {names}": "Some files can't be used with this tool: {names}",
    "이 형식은 사용할 수 없어요.": "This format isn't available.",
    "자동 (시스템 언어)": "Automatic (system language)",
    "언어를 바꾸려면 Swapeg를 다시 시작해야 합니다.\n지금 다시 시작할까요?":
        "Swapeg needs to restart to change the language.\nRestart now?",
}
