# ==============================================================
#  build.ps1 -- Pack json_viewer.py into a standalone Windows exe
#  Usage: .\build.ps1
# ==============================================================

$AppName   = "JSON_Viewer"
$EntryFile = "json_viewer.py"
$DistDir   = "dist"
$BuildDir  = "build"

# --- Check PyInstaller ---
Write-Host ">>> Checking PyInstaller..." -ForegroundColor Cyan

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "    PyInstaller not found, installing..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to install PyInstaller. Run manually: pip install pyinstaller"
        exit 1
    }
}

# --- Clean previous build artifacts ---
Write-Host ">>> Cleaning old build directories..." -ForegroundColor Cyan
if (Test-Path $DistDir)  { Remove-Item $DistDir  -Recurse -Force }
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }

$SpecFile = "$AppName.spec"
if (Test-Path $SpecFile) { Remove-Item $SpecFile -Force }

# --- Run PyInstaller ---
Write-Host ">>> Packing $EntryFile ..." -ForegroundColor Cyan

pyinstaller `
    --noconfirm `
    --onedir `
    --windowed `
    --name "$AppName" `
    "$EntryFile"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Packaging failed. Check the output above."
    exit 1
}

# --- Done ---
$ExePath = Join-Path $DistDir "$AppName\$AppName.exe"

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Build succeeded!" -ForegroundColor Green
Write-Host "  Output: $ExePath" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

