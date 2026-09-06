# Prompt 8 — финальная проверка (format, lint, typecheck, unit, integration, e2e)
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  param([string]$StartDir)
  $dir = $StartDir
  for ($i = 0; $i -lt 6; $i++) {
    if (Test-Path (Join-Path $dir "pnpm-workspace.yaml")) { return $dir }
    $parent = Split-Path $dir -Parent
    if (-not $parent -or $parent -eq $dir) { break }
    $dir = $parent
  }
  return $StartDir
}

$Root = Resolve-RepoRoot -StartDir (Split-Path $PSScriptRoot -Parent)
$ReportDir = Join-Path $Root "artifacts\prompt8"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
$Report = Join-Path $ReportDir "verification-report.txt"
$lines = @("Prompt 8 verification — $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')", "")

function Step([string]$Name, [scriptblock]$Block) {
  Write-Host "==> $Name"
  $lines += "==> $Name"
  try {
    & $Block
    if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    $lines += "PASS"
    Write-Host "PASS"
  } catch {
    $lines += "FAIL: $_"
    Write-Host "FAIL: $_"
    $script:Failed = $true
  }
  $lines += ""
}

$Failed = $false
Set-Location $Root

Step "build analysis PDF fixtures" {
  $py = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
  if (-not (Test-Path $py)) { $py = "python" }
  & $py (Join-Path $Root "tests\fixtures\upload\build_fixtures.py")
}

Step "format:check" { pnpm format:check }
Step "lint" { pnpm lint }
Step "typecheck" { pnpm typecheck }
Step "contracts:check" { pnpm contracts:check }
Step "unit (turbo test)" { pnpm test:unit }
Step "api integration (pytest)" { pnpm --filter @dar/api exec pytest tests -q --tb=short }
Step "smoke" { pnpm test:smoke }
Step "quality:eval" { pnpm quality:eval }
Step "quality:drills" { pnpm quality:drills }

$apiUp = $false
try {
  $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 3
  $apiUp = $r.StatusCode -eq 200
} catch { }

if (-not $apiUp) {
  $lines += "SKIP e2e full-stack: API not listening on :8000 (start scripts/windows/start-dar.ps1)"
  Write-Warning "API not up — UI-only e2e will run; full-stack tests skipped"
}

Step "e2e (playwright)" {
  if ($apiUp) {
    pnpm test:e2e
  } else {
    pnpm --filter @dar/web exec playwright test e2e/prompt8-final.spec.ts --grep "UI без API|axe|visual regression"
    pnpm --filter @dar/web exec playwright test e2e/ux.spec.ts e2e/auth-consent.spec.ts e2e/hardening.spec.ts
  }
}

$lines += "Overall: $(if ($Failed) { 'NO-GO (see failures above)' } else { 'GO pending manual review' })"
$lines | Set-Content -Path $Report -Encoding UTF8
Write-Host ""
Write-Host "Report: $Report"
if ($Failed) { exit 1 }
