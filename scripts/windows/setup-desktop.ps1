#Requires -Version 5.1
# Prepare desktop profile. Visible. Does not download PostgreSQL/Redis.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$LogDir = Join-Path $Root "artifacts\local-run"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Step([string]$Name, [scriptblock]$Body) {
  Write-Host "==> $Name"
  & $Body
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "Step failed: $Name" }
}

$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
$pyLauncher = $null
foreach ($c in @(
    @{ File = "py"; Args = @("-3.12") },
    @{ File = "py"; Args = @("-3.13") },
    @{ File = "python"; Args = @() }
  )) {
  if (Get-Command $c.File -ErrorAction SilentlyContinue) {
    $pyLauncher = $c
    break
  }
}
if (-not $pyLauncher) { throw "Python 3.12+ not found" }

if (-not (Test-Path $venvPy)) {
  Step "create venv" {
    & $pyLauncher.File @($pyLauncher.Args + @("-m", "venv", (Join-Path $Root "apps\api\.venv")))
  }
}

Step "pip install API" {
  & $venvPy -m pip install --upgrade pip
  & $venvPy -m pip install -r (Join-Path $Root "apps\api\requirements.txt")
  & $venvPy -m pip install -e (Join-Path $Root "packages\py_dar")
  & $venvPy -m pip install aiosqlite pytest httpx
}

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) { throw "Node.js 20+ not found" }

Step "web dependencies" {
  Push-Location $Root
  if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm install
  } else {
    corepack enable | Out-Null
    corepack pnpm install
  }
  Pop-Location
}

Step "production Next.js build" {
  Push-Location (Join-Path $Root "apps\web")
  $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
  if (Get-Command pnpm -ErrorAction SilentlyContinue) {
    pnpm build
  } else {
    corepack pnpm build
  }
  Pop-Location
}

Step "icon" {
  & $venvPy (Join-Path $PSScriptRoot "build-dar-icon.py")
}

$fontScript = Join-Path $PSScriptRoot "install-form-font.ps1"
if (Test-Path $fontScript) {
  Step "fonts" { & powershell -NoProfile -ExecutionPolicy Bypass -File $fontScript }
} else {
  Write-Host "==> font installer missing"
}

Step "sqlite schema" {
  $env:APP_ENV = "desktop"
  $data = Join-Path $env:LOCALAPPDATA "Docly\data"
  New-Item -ItemType Directory -Force -Path $data | Out-Null
  $env:DOCLY_DATA_DIR = $data
  $env:PYTHONPATH = (Join-Path $Root "apps\api") + [IO.Path]::PathSeparator + (Join-Path $Root "packages\py_dar\src")
  & $venvPy -c "from pathlib import Path; from app.desktop_boot import apply_desktop_env, migrate_sqlite; p=apply_desktop_env(data_dir=Path(r'$data')); migrate_sqlite(p); print(p)"
}

Step "shortcuts" {
  cscript //Nologo (Join-Path $PSScriptRoot "install-shortcuts.vbs")
}

Write-Host "Desktop setup complete. Double-click Docly."
