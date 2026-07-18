# AIUsageTracker build script - produces an unsigned single-file windowed exe.
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

Write-Host "Building AIUsageTracker.exe..." -ForegroundColor Cyan
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

if (Test-Path "dist\AIUsageTracker.exe") {
    $size = [math]::Round((Get-Item "dist\AIUsageTracker.exe").Length / 1MB, 1)
    Write-Host "Built dist\AIUsageTracker.exe ($size MB)" -ForegroundColor Green
} else {
    Write-Error "Build failed - dist\AIUsageTracker.exe not found"
    exit 1
}
