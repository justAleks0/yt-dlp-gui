# Build yt-dlp-gui as a Windows onedir app and optional Inno Setup installer.
# Requires Python 3.10+ on PATH with app dependencies installed.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$AppDir = Join-Path $RepoRoot "app"
$ReleaseDir = Join-Path $RepoRoot "release"
$InstallerScript = Join-Path $RepoRoot "installer\yt-dlp-gui.iss"

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

if (-not (Test-Path $ReleaseDir)) {
    New-Item -ItemType Directory -Path $ReleaseDir | Out-Null
}

$IsccCmd = Get-Command "iscc" -ErrorAction SilentlyContinue
$IsccPath = if ($IsccCmd) { $IsccCmd.Path } else { "" }
if (-not $IsccPath) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) {
        $IsccPath = $candidate
    }
}
if ($IsccPath -and (Test-Path $InstallerScript)) {
    Write-Host ""
    Write-Host "Building installer with Inno Setup..."
    & $IsccPath "/DRepoRoot=$RepoRoot" "/DAppVersion=dev" $InstallerScript

    $InstallerOut = Join-Path $ReleaseDir "yt-dlp-gui-installer.exe"
    if (Test-Path $InstallerOut) {
        $EasyAccessOut = Join-Path $RepoRoot "yt-dlp-gui-installer.exe"
        Copy-Item -Force $InstallerOut $EasyAccessOut
        Write-Host "Installer: $InstallerOut"
        Write-Host "Quick access: $EasyAccessOut"
    } else {
        Write-Warning "Inno Setup completed, but installer output was not found at: $InstallerOut"
    }
} else {
    Write-Host ""
    Write-Host "Skipping installer build (Inno Setup compiler 'iscc' not found)."
    Write-Host "Install Inno Setup 6 and rerun this script to produce a setup .exe."
}
