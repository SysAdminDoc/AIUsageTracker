# AIUsageTracker build script
# Produces: dist\AIUsageTracker.exe (portable) + dist\AIUsageTracker_Setup_<ver>.exe (installer)
# Usage: .\build.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Cleaning previous build artifacts..." -ForegroundColor Cyan
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item -Force *.spec -ErrorAction SilentlyContinue

# Ensure PyInstaller is available
python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Yellow
    python -m pip install pyinstaller
}

# Modules not used by this app - excluding them reduces exe size significantly.
$excludes = @(
    "numpy", "scipy", "pandas", "matplotlib", "tkinter.test",
    "unittest", "xmlrpc", "pydoc", "doctest", "argparse",
    "ftplib", "imaplib", "smtplib", "nntplib", "poplib", "telnetlib",
    "turtle", "turtledemo", "curses", "lib2to3", "ensurepip",
    "venv", "distutils", "setuptools", "pkg_resources", "pip",
    "PIL.ImageQt", "PIL.ImageTk"
)
$excludeArgs = ($excludes | ForEach-Object { "--exclude-module"; $_ })

Write-Host "Building AIUsageTracker.exe (portable)..." -ForegroundColor Cyan
python -m PyInstaller `
    --onefile `
    --windowed `
    --name AIUsageTracker `
    --icon "assets\app-logo.ico" `
    --add-data "assets\app-logo.png;assets" `
    --add-data "assets\app-logo.ico;assets" `
    --collect-all customtkinter `
    --collect-submodules windows_toasts `
    @excludeArgs `
    --clean --noconfirm `
    run.py

if (-not (Test-Path "dist\AIUsageTracker.exe")) {
    Write-Error "PyInstaller build failed - dist\AIUsageTracker.exe not found"
    exit 1
}

$size = [math]::Round((Get-Item "dist\AIUsageTracker.exe").Length / 1MB, 1)
Write-Host "Portable exe: dist\AIUsageTracker.exe ($size MB)" -ForegroundColor Green

# Build installer with Inno Setup
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe"
}

if (Test-Path $iscc) {
    Write-Host "Building installer with Inno Setup..." -ForegroundColor Cyan
    & $iscc /Q "installer.iss"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Inno Setup compilation failed"
        exit 1
    }
    $setupFile = Get-ChildItem "dist\AIUsageTracker_Setup_*.exe" | Select-Object -First 1
    if ($setupFile) {
        $setupSize = [math]::Round($setupFile.Length / 1MB, 1)
        Write-Host "Installer:    $($setupFile.Name) ($setupSize MB)" -ForegroundColor Green
    }
} else {
    Write-Host "Inno Setup not found - skipping installer build. Install from https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
}

Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "  Portable: dist\AIUsageTracker.exe" -ForegroundColor White
if ($setupFile) {
    Write-Host "  Installer: dist\$($setupFile.Name)" -ForegroundColor White
}
