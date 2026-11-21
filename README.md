# FFmpeg 변환기

파일을 넣고, 바꿀 형식을 고른 뒤, [바꾸기]만 누르면 되는 ffmpeg GUI (Python + PySide6).
화질은 원본 그대로 유지합니다 (가능하면 재인코딩 없이 복사, 필요하면 고화질 인코딩).

## 실행
`실행.bat`을 더블클릭하세요. 가상환경(.venv)이 없으면 만들고, `bin/`에 ffmpeg가 없으면 자동으로 내려받아 설치합니다(SHA-256 검증).

수동 실행:
```powershell
.\.venv\Scripts\python src\app.py
```

## 지원 형식
입력은 ffmpeg가 읽을 수 있는 파일이면 확장자와 무관하게 모두 받습니다.

- 영상(20): MP4, MKV, WebM, MOV, AVI, M4V, WMV, ASF, FLV, 3GP, 3G2, TS, MTS, M2TS, MPG, MPEG, VOB, OGV, GIF, APNG
- 오디오(18, 영상에서 소리 추출 포함): MP3, WAV, FLAC, M4A, AAC, OGG, OGA, OPUS, WMA, AIFF, AIF, AC3, MP2, MKA, AU, CAF, WV, TTA
- 이미지(17): PNG, JPG, JPEG, WebP, BMP, TIFF, TIF, ICO, TGA, PPM, JP2, PCX, SGI, QOI, EXR, AVIF

## 테스트
```powershell
.\.venv\Scripts\python -m pytest tests
```
(`bin/`에 ffmpeg가 있으면 실제 변환 테스트까지 실행합니다.)

## 배포(exe)
```powershell
.\.venv\Scripts\pip install pyinstaller
.\.venv\Scripts\pyinstaller --noconsole --name FFmpegGUI --paths src src\app.py
```
FFmpeg 빌드의 라이선스(GPL)를 확인하고 배포 시 고지하세요.
