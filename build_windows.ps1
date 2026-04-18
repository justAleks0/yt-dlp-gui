# Build yt-dlp-gui as a Windows onedir app (no separate installer; zip the folder to ship).
# Requires Python 3.10+ on PATH with app dependencies installed.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $RepoRoot "app"

Set-Location $AppDir

Write-Host "Installing build dependencies..."
python -m pip install -q -r (Join-Path $RepoRoot "requirements-build.txt")

Write-Host "Running PyInstaller..."
python -m PyInstaller yt-dlp-gui.spec --noconfirm

$Exe = Join-Path $AppDir "dist\yt-dlp-gui\yt-dlp-gui.exe"
if (-not (Test-Path $Exe)) {
    throw "Build failed: $Exe not found"
}

Write-Host ""
Write-Host "Built: $Exe"
Write-Host "Ship the whole folder: $(Join-Path $AppDir 'dist\yt-dlp-gui')"
Write-Host "First run copies bundled config.toml beside the exe if missing; edits save there."
