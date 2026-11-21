@echo off
cd /d "%~dp0"

rem 1) Create the virtual environment if missing
if not exist ".venv\Scripts\pythonw.exe" (
    echo Creating virtual environment...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
)

rem 2) Install ffmpeg into bin if missing (the app does not start without it)
if not exist "bin\ffmpeg.exe" goto install
if not exist "bin\ffprobe.exe" goto install
goto run

:install
echo ffmpeg not found in bin folder. Installing...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_ffmpeg.ps1"
if errorlevel 1 goto fail
if not exist "bin\ffmpeg.exe" goto fail
if not exist "bin\ffprobe.exe" goto fail

:run
start "" ".venv\Scripts\pythonw.exe" src\app.py
exit /b 0

:fail
echo.
echo ffmpeg installation failed. The app will not start.
echo Check your internet connection, or copy ffmpeg.exe and ffprobe.exe into the bin folder manually.
pause
exit /b 1
