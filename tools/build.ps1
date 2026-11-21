# Builds Swapeg: PyInstaller one-folder app, portable zip, and the Setup installer (Inno Setup 6).
# ALL build output goes OUTSIDE the source folder: <parent of project>\swapeg-build  (or -Out <dir>)
# Keep this file ASCII-only: Windows PowerShell 5.1 misreads BOM-less UTF-8.
param([string]$Out = '')
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
if (-not $Out) { $Out = Join-Path (Split-Path $root -Parent) 'swapeg-build' }
$Out = [IO.Path]::GetFullPath($Out)
if ($Out -eq $root -or $Out.StartsWith($root + '\')) { throw "Output dir must be outside the source folder: $Out" }
New-Item -ItemType Directory -Force $Out | Out-Null

# Inno Setup compiler
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Inno Setup 6 (ISCC.exe) not found.' }

Set-Location $root
$py = Join-Path $root '.venv\Scripts\python.exe'
$version = (& $py -c "import sys; sys.path.insert(0, 'src'); from version import __version__; print(__version__)").Trim()
Write-Host "Building Swapeg $version -> $Out"

# 1) App
& $py -m pip install -q pyinstaller
$work = Join-Path $Out 'work'
$dist = Join-Path $Out 'dist'
Remove-Item $work, $dist -Recurse -Force -ErrorAction SilentlyContinue
# Absolute paths everywhere: PyInstaller resolves relative ones against --specpath (the output dir).
& $py -m PyInstaller --noconfirm --noconsole --name Swapeg --icon (Join-Path $root 'assets\icon.ico') `
    --paths (Join-Path $root 'src') --distpath $dist --workpath $work --specpath $Out `
    --exclude-module tkinter --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick `
    --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.Qt3DCore `
    (Join-Path $root 'src\app.py')
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }

$app = Join-Path $dist 'Swapeg'
Copy-Item assets (Join-Path $app 'assets') -Recurse -Force          # icons used at runtime
New-Item -ItemType Directory -Force (Join-Path $app 'bin') | Out-Null  # ffmpeg is installed here on first run
Copy-Item README.md $app -Force

$rel = Join-Path $Out 'releases'
New-Item -ItemType Directory -Force $rel | Out-Null

# 2) Portable zip
$zip = Join-Path $rel "Swapeg-$version-win64.zip"
Remove-Item $zip -Force -ErrorAction SilentlyContinue
Compress-Archive -Path $app -DestinationPath $zip -CompressionLevel Optimal

# 3) Installer
$setup = Join-Path $rel "Swapeg-$version-Setup.exe"
Remove-Item $setup -Force -ErrorAction SilentlyContinue
$env:SWAPEG_VERSION = $version
$env:SWAPEG_ROOT = $root
$env:SWAPEG_DIST = $app
$env:SWAPEG_OUT = $rel
& $iscc /Q (Join-Path $root 'installer\Swapeg.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed.' }

# 4) Checksums
$sums = foreach ($f in @($setup, $zip)) {
    "{0}  {1}" -f (Get-FileHash $f -Algorithm SHA256).Hash.ToLower(), (Split-Path $f -Leaf)
}
$sums | Set-Content (Join-Path $rel 'SHA256SUMS.txt') -Encoding ascii
Write-Host ''
Get-ChildItem $rel | ForEach-Object { Write-Host ("{0,-34} {1,8:N1} MB" -f $_.Name, ($_.Length / 1MB)) }
