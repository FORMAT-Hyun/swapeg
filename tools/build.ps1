# Builds Swapeg (PyInstaller, one-folder) and packs releases\Swapeg-<version>-win64.zip
# Keep this file ASCII-only: Windows PowerShell 5.1 misreads BOM-less UTF-8.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root '.venv\Scripts\python.exe'

$version = (& $py -c "import sys; sys.path.insert(0, 'src'); from version import __version__; print(__version__)").Trim()
Write-Host "Building Swapeg $version ..."

& $py -m pip install -q pyinstaller
Remove-Item build, dist -Recurse -Force -ErrorAction SilentlyContinue
& $py -m PyInstaller --noconfirm --noconsole --name Swapeg --icon assets\icon.ico --paths src `
    --exclude-module tkinter --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore `
    src\app.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

$app = Join-Path $root 'dist\Swapeg'
Copy-Item assets (Join-Path $app 'assets') -Recurse -Force          # icons used at runtime
New-Item -ItemType Directory -Force (Join-Path $app 'bin') | Out-Null  # ffmpeg is installed here on first run
Copy-Item README.md $app -Force

New-Item -ItemType Directory -Force releases | Out-Null
$zip = Join-Path $root "releases\Swapeg-$version-win64.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $app -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLower()
"$hash  Swapeg-$version-win64.zip" | Set-Content (Join-Path $root "releases\Swapeg-$version-win64.zip.sha256") -Encoding ascii
Write-Host ("Done: {0} ({1:N1} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))
Write-Host "SHA256: $hash"
