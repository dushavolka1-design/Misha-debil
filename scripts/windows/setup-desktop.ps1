#Requires -Version 5.1
# Build the source-based desktop profile. This is not a binary installer.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

function Invoke-Checked {
  param([string]$File, [string[]]$Arguments)
  & $File @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed (exit $LASTEXITCODE): $File"
  }
}

# Probe the actual interpreter, not just whether the Windows py launcher exists.
$pyLauncher = $null
foreach ($candidate in @(
    @{ File = "py"; Args = @("-3.12") },
    @{ File = "py"; Args = @("-3.13") },
    @{ File = "python"; Args = @() }
  )) {
  if (-not (Get-Command $candidate.File -ErrorAction SilentlyContinue)) { continue }
  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    & $candidate.File @($candidate.Args + @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)")) 2>$null
    $probeExit = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousPreference
  }
  if ($probeExit -eq 0) { $pyLauncher = $candidate; break }
}
if (-not $pyLauncher) { throw "Python 3.12+ not found. Install Python and try again." }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js 20+ not found" }
Invoke-Checked -File "node" -Arguments @("-e", "process.exit(Number(process.versions.node.split('.')[0]) >= 20 ? 0 : 1)")

$pnpmFile = "pnpm"
$pnpmPrefix = @()
if (-not (Get-Command pnpm -ErrorAction SilentlyContinue)) {
  if (-not (Get-Command corepack -ErrorAction SilentlyContinue)) {
    throw "pnpm 9.15.9 or Corepack is required. See package.json packageManager."
  }
  $pnpmFile = "corepack"
  $pnpmPrefix = @("pnpm")
}
Push-Location $Root
try {
  $pnpmVersion = & $pnpmFile @($pnpmPrefix + @("--version"))
  if ($LASTEXITCODE -ne 0 -or ($pnpmVersion | Select-Object -Last 1).Trim() -ne "9.15.9") {
    throw "Use pnpm 9.15.9, as pinned in package.json."
  }
} finally { Pop-Location }

$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "==> create venv"
  Invoke-Checked -File $pyLauncher.File -Arguments @($pyLauncher.Args + @("-m", "venv", (Join-Path $Root "apps\api\.venv")))
}
Invoke-Checked -File $venvPy -Arguments @("-c", "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)")

Write-Host "==> API dependencies"
Invoke-Checked -File $venvPy -Arguments @("-m", "pip", "install", "--upgrade", "pip")
Invoke-Checked -File $venvPy -Arguments @("-m", "pip", "install", "-r", (Join-Path $Root "apps\api\requirements.txt"))
Invoke-Checked -File $venvPy -Arguments @("-m", "pip", "install", "-e", (Join-Path $Root "packages\py_dar"))
Invoke-Checked -File $venvPy -Arguments @("-m", "pip", "install", "pytest", "httpx")

Push-Location $Root
try {
  Write-Host "==> locked web dependencies"
  Invoke-Checked -File $pnpmFile -Arguments @($pnpmPrefix + @("install", "--frozen-lockfile"))
  Write-Host "==> production Next.js build"
  $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
  Invoke-Checked -File $pnpmFile -Arguments @($pnpmPrefix + @("--filter", "@dar/web", "build"))
} finally { Pop-Location }
if (-not (Test-Path (Join-Path $Root "apps\web\.next\BUILD_ID"))) {
  throw "Production web BUILD_ID was not created"
}

Write-Host "==> desktop assets"
Invoke-Checked -File $venvPy -Arguments @((Join-Path $PSScriptRoot "build-dar-icon.py"))
$fontScript = Join-Path $PSScriptRoot "install-form-font.ps1"
if (-not (Test-Path $fontScript)) { throw "Form font installer missing: $fontScript" }
Invoke-Checked -File "powershell" -Arguments @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $fontScript)

Write-Host "==> SQLite schema"
$env:APP_ENV = "desktop"
if (-not $env:DOCLY_DATA_DIR) {
  if (-not $env:LOCALAPPDATA) { throw "LOCALAPPDATA is missing; set DOCLY_DATA_DIR explicitly" }
  $env:DOCLY_DATA_DIR = Join-Path $env:LOCALAPPDATA "Docly\data"
}
$env:PYTHONPATH = (Join-Path $Root "apps\api") + [IO.Path]::PathSeparator + (Join-Path $Root "packages\py_dar\src")
# Read the path from the environment: apostrophes, spaces and Unicode are not code.
Invoke-Checked -File $venvPy -Arguments @("-c", "import os; from pathlib import Path; from app.desktop_boot import apply_desktop_env, migrate_sqlite; p=apply_desktop_env(data_dir=Path(os.environ['DOCLY_DATA_DIR'])); migrate_sqlite(p); print(p)")

Write-Host "==> shortcuts"
Invoke-Checked -File "cscript" -Arguments @("//Nologo", (Join-Path $PSScriptRoot "install-shortcuts.vbs"))
Write-Host "Desktop source setup complete. Double-click Docly."
