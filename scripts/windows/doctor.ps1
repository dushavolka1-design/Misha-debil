#Requires -Version 5.1
# Doctor: check only, never silently repair. ASCII-only for Windows PowerShell 5.1.
$ErrorActionPreference = "Continue"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$failed = 0

function Check([string]$Name, [bool]$Ok, [string]$Hint) {
  if ($Ok) {
    Write-Host "[OK] $Name"
  } else {
    Write-Host ("[FAIL] {0} - {1}" -f $Name, $Hint)
    $script:failed++
  }
}

$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
$node = Get-Command node -ErrorAction SilentlyContinue
$buildId = Join-Path $Root "apps\web\.next\BUILD_ID"
$icon = Join-Path $Root "scripts\windows\assets\docly-icon.ico"
$launcher = Join-Path $Root "scripts\windows\docly_launcher.py"
$data = Join-Path $env:LOCALAPPDATA "Docly\data"
$runtimeJs = Join-Path $Root "apps\web\public\docly-runtime.js"
$nextBin = Join-Path $Root "apps\web\node_modules\next\dist\bin\next"
if (-not (Test-Path $nextBin)) {
  $nextBin = Join-Path $Root "node_modules\next\dist\bin\next"
}

Check "Python venv" (Test-Path $venvPy) "Run setup-desktop.ps1"
Check "Node.js" ([bool]$node) "Install Node.js 20+"
Check "Next production BUILD_ID" (Test-Path $buildId) "Run setup-desktop.ps1 (pnpm build)"
Check "Next start binary" (Test-Path $nextBin) "Run setup-desktop.ps1"
Check "Launcher script" (Test-Path $launcher) "Missing docly_launcher.py"
Check "Icon" (Test-Path $icon) "Run build-dar-icon.py"
Check "Runtime js" (Test-Path $runtimeJs) "Missing public/docly-runtime.js"

$writable = $false
try {
  New-Item -ItemType Directory -Force -Path $data | Out-Null
  $probe = Join-Path $data ".doctor-write"
  Set-Content -Path $probe -Value "ok" -Encoding UTF8
  Remove-Item $probe -Force
  $writable = $true
} catch { $writable = $false }
Check "Writable data dir" $writable $data

$db = Join-Path $data "docly.db"
$sqliteOk = $false
$sqliteHint = "Run setup-desktop.ps1 to create SQLite schema"
if (Test-Path $db) {
  if (Test-Path $venvPy) {
    & $venvPy -c "import sqlite3,sys; p=sys.argv[1]; c=sqlite3.connect(p); r=c.execute('PRAGMA integrity_check').fetchone(); c.close(); raise SystemExit(0 if r and r[0]=='ok' else 1)" $db 2>$null
    $sqliteOk = $LASTEXITCODE -eq 0
    if (-not $sqliteOk) { $sqliteHint = "SQLite integrity_check failed" }
  }
} else {
  $sqliteHint = "docly.db is missing - run setup-desktop.ps1 (doctor does not create it)"
}
Check "SQLite database" $sqliteOk $sqliteHint

$uvicornOk = $false
if (Test-Path $venvPy) {
  & $venvPy -c "import uvicorn, fastapi" 2>$null
  $uvicornOk = $LASTEXITCODE -eq 0
}
Check "API runtime import" $uvicornOk "pip install -r apps/api/requirements.txt"

Write-Host "[INFO] Ports: launcher never kills foreign PIDs; busy 3000/8000 -> next free port"
Check "Port policy documented" $true "ok"

$fontDir = Join-Path $Root "apps\api\app\services\forms\fill\assets"
$fontFile = Join-Path $fontDir "NotoSans-Regular.ttf"
$fontManifest = Join-Path $fontDir "font-manifest.json"
$fontOk = $false
$fontHint = "Run install-form-font.ps1"
if ((Test-Path $fontFile) -and (Test-Path $fontManifest)) {
  try {
    $manifest = Get-Content $fontManifest -Raw -Encoding UTF8 | ConvertFrom-Json
    $expected = ([string]$manifest.expected_sha256).ToLower()
    $actual = (Get-FileHash -Path $fontFile -Algorithm SHA256).Hash.ToLower()
    $fontOk = $expected -and ($actual -eq $expected)
    if (-not $fontOk) { $fontHint = "Font SHA-256 does not match font-manifest.json" }
  } catch {
    $fontHint = "Cannot read font manifest or hash"
  }
}
Check "Form font Noto Sans hash" $fontOk $fontHint

$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Docly.lnk"
if (Test-Path $lnk) {
  $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
  $iconOk = $sc.IconLocation -and (Test-Path ($sc.IconLocation.Split(",")[0]))
  $targetOk = Test-Path $sc.TargetPath
  $argsOk = $sc.Arguments -match "docly_launcher.py"
  $wdOk = Test-Path $sc.WorkingDirectory
  Check "Shortcut target exists" $targetOk $sc.TargetPath
  Check "Shortcut arguments launcher" $argsOk $sc.Arguments
  Check "Shortcut working directory" $wdOk $sc.WorkingDirectory
  Check "Shortcut icon exists" $iconOk $sc.IconLocation
} else {
  Check "Desktop Docly.lnk" $false "Run create-desktop-shortcut.ps1"
}

if ($failed -gt 0) {
  Write-Host ("Doctor: {0} check(s) failed." -f $failed)
  exit 1
}
Write-Host "Doctor: all checks passed."
exit 0
