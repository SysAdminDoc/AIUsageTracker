# Build the portable executable and the per-user installer from a clean output.
param([string]$Python = "$PSScriptRoot/.venv/Scripts/python.exe")
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath($PSScriptRoot)
Set-Location -LiteralPath $repoRoot
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Create .venv and install requirements-dev.txt first. See README.md.'
}
$compilerCandidates = @(
    "$env:LOCALAPPDATA/Programs/Inno Setup 6/ISCC.exe",
    'C:/Program Files (x86)/Inno Setup 6/ISCC.exe',
    'C:/Program Files/Inno Setup 6/ISCC.exe'
)
$compiler = $compilerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $compiler) { throw 'Install Inno Setup 6 before building the installer.' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed. Build stopped.' }
foreach ($name in @('build', 'dist')) {
    $target = [IO.Path]::GetFullPath((Join-Path $repoRoot $name))
    if ([IO.Path]::GetDirectoryName($target) -ne $repoRoot) { throw "Unsafe build directory: $target" }
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
& $Python -m PyInstaller --clean --noconfirm AIUsageTracker.spec
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath 'dist/AIUsageTracker.exe')) {
    throw 'Portable build failed.'
}
& $compiler /Q installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
$version = & $Python -c 'from aiusagetracker import __version__; print(__version__)'
if (-not (Test-Path -LiteralPath "dist/AIUsageTracker_Setup_$version.exe")) { throw 'Installer is missing.' }
Copy-Item -LiteralPath LICENSE, THIRD-PARTY-NOTICES.txt -Destination dist
Compress-Archive -LiteralPath 'dist/AIUsageTracker.exe', 'dist/LICENSE', 'dist/THIRD-PARTY-NOTICES.txt' -DestinationPath "dist/AIUsageTracker-portable-v$version.zip"
Write-Host "AIUsageTracker v$version built. Executable and installer are unsigned."
