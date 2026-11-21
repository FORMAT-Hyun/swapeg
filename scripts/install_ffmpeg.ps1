# Installs ffmpeg.exe / ffprobe.exe into ..\bin (gyan.dev release build, SHA-256 verified).
# Keep this file ASCII-only: Windows PowerShell 5.1 misreads BOM-less UTF-8.
$ErrorActionPreference = 'Stop'
$url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
$bin = Join-Path (Split-Path $PSScriptRoot -Parent) 'bin'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ('swapeg-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $bin, $tmp | Out-Null

try {
    Write-Host 'Fetching checksum...'
    $expected = ((New-Object Net.WebClient).DownloadString("$url.sha256").Trim() -split '\s+')[0].ToLower()
    if ($expected -notmatch '^[0-9a-f]{64}$') { throw 'Could not get checksum.' }

    Write-Host 'Downloading ffmpeg (about 100MB)...'
    $zip = Join-Path $tmp 'ffmpeg.zip'
    & curl.exe -L --fail -o $zip $url
    if ($LASTEXITCODE -ne 0) { throw 'Download failed.' }

    if ((Get-FileHash $zip -Algorithm SHA256).Hash.ToLower() -ne $expected) {
        throw 'Checksum mismatch (corrupted or tampered download).'
    }

    Write-Host 'Extracting...'
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $z = [IO.Compression.ZipFile]::OpenRead($zip)
    try {
        foreach ($e in $z.Entries) {
            if ($e.FullName -match '/bin/(ffmpeg|ffprobe)\.exe$') {
                [IO.Compression.ZipFileExtensions]::ExtractToFile($e, (Join-Path $bin $e.Name), $true)
            }
        }
    } finally { $z.Dispose() }

    foreach ($n in 'ffmpeg.exe', 'ffprobe.exe') {
        if (-not (Test-Path (Join-Path $bin $n))) { throw "$n not found in archive." }
    }
    Write-Host 'ffmpeg installed.'
}
catch {
    Write-Host "Install failed: $($_.Exception.Message)"
    exit 1
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
