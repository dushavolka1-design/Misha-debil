#Requires -Version 5.1
# Full desktop launcher e2e. Does not download PostgreSQL/Redis. Does not use Docker.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
$failed = 0

function Assert-True([bool]$Ok, [string]$Name) {
  if ($Ok) { Write-Host "[OK] $Name" }
  else { Write-Host "[FAIL] $Name"; $script:failed++ }
}

if (-not (Test-Path $venvPy)) {
  Write-Error "Missing API venv. Run setup-desktop.ps1 first."
  exit 1
}

& $venvPy (Join-Path $PSScriptRoot "build-dar-icon.py")
Assert-True (Test-Path (Join-Path $PSScriptRoot "assets\docly-icon.ico")) "icon exists"

Push-Location $Root
$env:PYTHONPATH = (Join-Path $Root "apps\api") + [IO.Path]::PathSeparator + (Join-Path $Root "packages\py_dar\src")
& $venvPy -m pytest apps/api/tests/test_desktop_launcher_contract.py apps/api/tests/test_desktop_profile.py apps/api/tests/test_desktop_launcher_e2e.py apps/api/tests/test_desktop_http.py -q --tb=short
Assert-True ($LASTEXITCODE -eq 0) "pytest desktop suite"
Pop-Location

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "create-desktop-shortcut.ps1")
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Docly.lnk"
Assert-True (Test-Path $lnk) "Docly.lnk on desktop"
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
Assert-True (Test-Path $sc.TargetPath) "shortcut target exists"
Assert-True ($sc.Arguments -match "docly_launcher.py") "shortcut args launcher"
Assert-True (Test-Path $sc.WorkingDirectory) "shortcut working directory"
$iconFile = $sc.IconLocation.Split(",")[0]
Assert-True (Test-Path $iconFile) "shortcut icon exists"

$buildId = Join-Path $Root "apps\web\.next\BUILD_ID"
if (-not (Test-Path $buildId)) {
  Write-Host "[FAIL] missing production BUILD_ID - run setup-desktop.ps1"
  $failed++
} else {
  $tmp = Join-Path $env:TEMP ("docly-e2e-" + [guid]::NewGuid().ToString("N"))
  $data = Join-Path $tmp "Docly Data"
  $runtime = Join-Path $tmp "runtime"
  New-Item -ItemType Directory -Force -Path $data, $runtime | Out-Null

  $busy8000 = $null
  $busy3000 = $null
  try {
    $busy8000 = New-Object System.Net.Sockets.TcpListener ([Net.IPAddress]::Loopback, 8000)
    $busy8000.Start()
    $busy3000 = New-Object System.Net.Sockets.TcpListener ([Net.IPAddress]::Loopback, 3000)
    $busy3000.Start()
  } catch {
    Write-Host "[INFO] could not occupy 3000/8000"
  }

  $env:DOCLY_HEADLESS = "1"
  $env:DOCLY_NO_BROWSER = "1"
  $env:DOCLY_DATA_DIR = $data
  $env:DOCLY_RUNTIME_DIR = $runtime
  $launcher = Join-Path $PSScriptRoot "docly_launcher.py"

  & $venvPy $launcher --headless
  $first = $LASTEXITCODE
  Assert-True ($first -eq 0) "first headless start"

  $instFile = Join-Path $runtime "instance.json"
  Assert-True (Test-Path $instFile) "instance.json written"
  if (Test-Path $instFile) {
    $inst = Get-Content $instFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($busy8000) { Assert-True ($inst.api_port -ne 8000) "skipped busy API 8000" }
    if ($busy3000) { Assert-True ($inst.web_port -ne 3000) "skipped busy web 3000" }

    try {
      $live = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/live" -f $inst.api_port) -UseBasicParsing -TimeoutSec 5
      Assert-True ($live.StatusCode -eq 200) "API /live 200"
    } catch { Assert-True $false "API /live 200" }
    try {
      $ready = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/ready" -f $inst.api_port) -UseBasicParsing -TimeoutSec 5
      Assert-True ($ready.StatusCode -eq 200) "API /ready 200"
    } catch { Assert-True $false "API /ready 200" }
    try {
      $web = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/" -f $inst.web_port) -UseBasicParsing -TimeoutSec 10
      Assert-True ($web.StatusCode -eq 200) "web 200"
    } catch { Assert-True $false "web 200" }
    try {
      $ident = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/instance" -f $inst.api_port) -UseBasicParsing -TimeoutSec 5
      Assert-True ($ident.Content -match "docly") "instance identity"
    } catch { Assert-True $false "instance identity" }

    $db = Join-Path $data "docly.db"
    Assert-True (Test-Path $db) "sqlite persisted"

    & $venvPy $launcher --headless
    Assert-True ($LASTEXITCODE -eq 0) "second start already-running"

    & $venvPy $launcher --stop
    Assert-True ($LASTEXITCODE -eq 0) "stop"
    Start-Sleep -Seconds 1
    $apiAlive = $false
    $webAlive = $false
    try { $null = Get-Process -Id $inst.api_pid -ErrorAction Stop; $apiAlive = $true } catch {}
    try { $null = Get-Process -Id $inst.web_pid -ErrorAction Stop; $webAlive = $true } catch {}
    Assert-True (-not $apiAlive) "api process stopped"
    Assert-True (-not $webAlive) "web process stopped"
  }

  if ($busy8000) { $busy8000.Stop() }
  if ($busy3000) { $busy3000.Stop() }

  Remove-Item Env:DOCLY_HEADLESS -ErrorAction SilentlyContinue
  Remove-Item Env:DOCLY_NO_BROWSER -ErrorAction SilentlyContinue
  Remove-Item Env:DOCLY_DATA_DIR -ErrorAction SilentlyContinue
  Remove-Item Env:DOCLY_RUNTIME_DIR -ErrorAction SilentlyContinue
}

if ($failed -gt 0) {
  Write-Host ("Launcher e2e: {0} check(s) failed." -f $failed)
  exit 1
}
Write-Host "Launcher e2e: all checks passed."
exit 0
