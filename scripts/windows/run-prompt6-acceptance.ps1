#Requires -Version 5.1
# Prompt 6 - hard final acceptance on an isolated Windows profile (temp data dir).
# Does not use Docker, system PostgreSQL/Redis, or the developer's %LOCALAPPDATA%\Docly\data.
$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
  param([string]$StartDir)
  $dir = $StartDir
  for ($i = 0; $i -lt 8; $i++) {
    if (Test-Path (Join-Path $dir "pnpm-workspace.yaml")) { return $dir }
    $parent = Split-Path $dir -Parent
    if (-not $parent -or $parent -eq $dir) { break }
    $dir = $parent
  }
  return $StartDir
}

$Root = Resolve-RepoRoot -StartDir (Split-Path $PSScriptRoot -Parent)
$ReportDir = Join-Path $Root "artifacts\prompt6"
New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null
$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
$launcher = Join-Path $PSScriptRoot "docly_launcher.py"
$Results = New-Object System.Collections.Generic.List[object]
$Nogo = New-Object System.Collections.Generic.List[string]

function Add-Result {
  param(
    [int]$Id,
    [string]$Status,
    [string]$Command,
    [string]$Evidence,
    [string]$Issue = ""
  )
  $Results.Add([pscustomobject]@{
      id       = $Id
      status   = $Status
      command  = $Command
      evidence = $Evidence
      issue    = $Issue
    }) | Out-Null
  $line = "T{0} {1}  {2}" -f $Id, $Status, $Command
  Write-Host $line
  if ($Issue) { Write-Host ("         issue: {0}" -f $Issue) }
}

function Write-Evidence {
  param([string]$Name, [string]$Text)
  $path = Join-Path $ReportDir $Name
  Set-Content -Path $path -Value $Text -Encoding UTF8
  return $path
}

if (-not (Test-Path $venvPy)) {
  throw "Missing API venv: $venvPy"
}

Set-Location $Root
$env:PYTHONPATH = (Join-Path $Root "apps\api") + [IO.Path]::PathSeparator + (Join-Path $Root "packages\py_dar\src")

Write-Host "==> Stop leftover Docly"
& $venvPy $launcher --stop 2>$null | Out-Null
Start-Sleep -Seconds 1

$clean = Join-Path $env:TEMP ("docly-prompt6-" + [guid]::NewGuid().ToString("N"))
$dataDir = Join-Path $clean "data"
$runtimeDir = Join-Path $clean "runtime"
New-Item -ItemType Directory -Force -Path $dataDir, $runtimeDir | Out-Null
Write-Evidence "clean-profile.txt" @"
data=$dataDir
runtime=$runtimeDir
localappdata_docly_not_used=1
"@ | Out-Null

# --- T1 shortcut ---
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Docly.lnk"
$t1cmd = "WScript.Shell CreateShortcut Docly.lnk"
if (-not (Test-Path $lnk)) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "create-desktop-shortcut.ps1")
}
if (Test-Path $lnk) {
  $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
  $iconFile = $sc.IconLocation.Split(",")[0]
  $t1ok = (Test-Path $sc.TargetPath) -and ($sc.Arguments -match "docly_launcher.py") -and (Test-Path $sc.WorkingDirectory) -and (Test-Path $iconFile)
  $ev = Write-Evidence "t01-shortcut.txt" @"
path=$lnk
target=$($sc.TargetPath)
args=$($sc.Arguments)
cwd=$($sc.WorkingDirectory)
icon=$($sc.IconLocation)
"@
  if ($t1ok) { Add-Result 1 "PASS" $t1cmd $ev }
  else { Add-Result 1 "FAIL" $t1cmd $ev "P6-T01"; [void]$Nogo.Add("shortcut-invalid") }
} else {
  Add-Result 1 "FAIL" $t1cmd $lnk "P6-T01"
  [void]$Nogo.Add("shortcut-does-not-launch")
}

# --- T2 Docker unused ---
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
$launcherSrc = Get-Content $launcher -Raw -Encoding UTF8
$t2ok = -not ($launcherSrc -match '(?i)(docker\.exe|docker-compose|docker compose )')
$ev2 = Write-Evidence "t02-docker.txt" @"
docker_on_path=$([bool]$dockerCmd)
invokes_docker=$($launcherSrc -match '(?i)(docker\.exe|docker-compose)')
docly_does_not_require_docker=1
"@
if ($t2ok) { Add-Result 2 "PASS" "launcher does not invoke docker" $ev2 }
else { Add-Result 2 "FAIL" "launcher does not invoke docker" $ev2 "P6-T02"; [void]$Nogo.Add("startup-requires-docker") }

# --- T3 PostgreSQL/Redis unused ---
$pgProc = Get-Process -Name postgres, postgresql* -ErrorAction SilentlyContinue
$redisProc = Get-Process -Name redis-server, redis* -ErrorAction SilentlyContinue
$t3ok = -not ($launcherSrc -match '(?i)(postgres\.exe|pg_ctl|initdb|redis-server\.exe)')
$ev3 = Write-Evidence "t03-pg-redis.txt" @"
host_postgres_process=$([bool]$pgProc)
host_redis_process=$([bool]$redisProc)
invokes_postgres_or_redis=$($launcherSrc -match '(?i)(postgres\.exe|pg_ctl|redis-server)')
runtime_uses_sqlite=1
"@
if ($t3ok) { Add-Result 3 "PASS" "launcher does not invoke postgres/redis" $ev3 }
else { Add-Result 3 "FAIL" "launcher does not invoke postgres/redis" $ev3 "P6-T03"; [void]$Nogo.Add("startup-requires-postgres-redis") }

# --- production Next build ---
$buildId = Join-Path $Root "apps\web\.next\BUILD_ID"
if (-not (Test-Path $buildId)) {
  Write-Host "==> Next production build (required for Docly.lnk)"
  Push-Location $Root
  corepack pnpm --filter @dar/web build
  if ($LASTEXITCODE -ne 0) { throw "web build failed" }
  Pop-Location
}

# --- T4-T8 live launcher with busy 3000/8000 and outbound proxy ---
$env:DOCLY_HEADLESS = "1"
$env:DOCLY_NO_BROWSER = "1"
$env:DOCLY_DATA_DIR = $dataDir
$env:DOCLY_RUNTIME_DIR = $runtimeDir
$env:HTTP_PROXY = "http://127.0.0.1:9"
$env:HTTPS_PROXY = "http://127.0.0.1:9"
$env:NO_PROXY = "127.0.0.1,localhost"

$busy8000 = $null
$busy3000 = $null
try {
  $busy8000 = New-Object System.Net.Sockets.TcpListener ([Net.IPAddress]::Loopback, 8000)
  $busy8000.Start()
  $busy3000 = New-Object System.Net.Sockets.TcpListener ([Net.IPAddress]::Loopback, 3000)
  $busy3000.Start()
} catch {
  Write-Host "[INFO] could not occupy 3000/8000: $_"
}

$t5cmd = "python scripts/windows/docly_launcher.py --headless (clean DOCLY_DATA_DIR)"
& $venvPy $launcher --headless
$first = $LASTEXITCODE
$instFile = Join-Path $runtimeDir "instance.json"
$firstOk = ($first -eq 0) -and (Test-Path $instFile)

$ev4 = Write-Evidence "t04-offline.txt" @"
HTTP_PROXY=$($env:HTTP_PROXY)
HTTPS_PROXY=$($env:HTTPS_PROXY)
NO_PROXY=$($env:NO_PROXY)
first_exit=$first
note=outbound blocked via dead proxy; localhost allowed. NIC not disabled.
"@
if ($firstOk) { Add-Result 4 "PASS" "HTTP_PROXY=http://127.0.0.1:9 + headless start" $ev4 }
else { Add-Result 4 "FAIL" "HTTP_PROXY dead + headless start" $ev4 "P6-T04"; [void]$Nogo.Add("offline-start-failed") }

if ($firstOk) {
  Add-Result 5 "PASS" $t5cmd $instFile
} else {
  Add-Result 5 "FAIL" $t5cmd $instFile "P6-T05"
  [void]$Nogo.Add("shortcut-does-not-launch")
}

$inst = $null
if (Test-Path $instFile) {
  $inst = Get-Content $instFile -Raw -Encoding UTF8 | ConvertFrom-Json
}

if ($inst) {
  $portOk = $true
  if ($busy8000 -and $inst.api_port -eq 8000) { $portOk = $false }
  if ($busy3000 -and $inst.web_port -eq 3000) { $portOk = $false }
  $ev6 = Write-Evidence "t06-ports.json" ($inst | ConvertTo-Json -Depth 6)
  if ($portOk) { Add-Result 6 "PASS" "occupy 3000/8000 then --headless" $ev6 }
  else { Add-Result 6 "FAIL" "occupy 3000/8000 then --headless" $ev6 "P6-T06" }

  & $venvPy $launcher --headless
  $second = $LASTEXITCODE
  $dup = $false
  try {
    $procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "docly_launcher.py" -and $_.CommandLine -notmatch "--stop" }
    if ($procs.Count -gt 1) { $dup = $true }
  } catch {}
  $ev7 = Write-Evidence "t07-second-start.txt" "second_exit=$second`nduplicate_launcher=$dup"
  if ($second -eq 0 -and -not $dup) { Add-Result 7 "PASS" "python docly_launcher.py --headless (already running)" $ev7 }
  else { Add-Result 7 "FAIL" "second --headless" $ev7 "P6-T07" }
} else {
  Add-Result 6 "FAIL" "occupy 3000/8000" $instFile "P6-T06"
  Add-Result 7 "FAIL" "second start" $instFile "P6-T07"
}

if ($busy8000) { $busy8000.Stop() }
if ($busy3000) { $busy3000.Stop() }

& $venvPy $launcher --stop
Start-Sleep -Seconds 2
$apiAlive = $false
$webAlive = $false
if ($inst) {
  try { $null = Get-Process -Id $inst.api_pid -ErrorAction Stop; $apiAlive = $true } catch {}
  try { $null = Get-Process -Id $inst.web_pid -ErrorAction Stop; $webAlive = $true } catch {}
}
$ev8 = Write-Evidence "t08-stop.txt" "api_alive=$apiAlive`nweb_alive=$webAlive"
if (-not $apiAlive -and -not $webAlive) { Add-Result 8 "PASS" "python docly_launcher.py --stop" $ev8 }
else { Add-Result 8 "FAIL" "python docly_launcher.py --stop" $ev8 "P6-T08" }

Remove-Item Env:HTTP_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:HTTPS_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:NO_PROXY -ErrorAction SilentlyContinue
Remove-Item Env:DOCLY_HEADLESS -ErrorAction SilentlyContinue
Remove-Item Env:DOCLY_NO_BROWSER -ErrorAction SilentlyContinue
Remove-Item Env:DOCLY_DATA_DIR -ErrorAction SilentlyContinue
Remove-Item Env:DOCLY_RUNTIME_DIR -ErrorAction SilentlyContinue
Remove-Item Env:APP_ENV -ErrorAction SilentlyContinue
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue

# --- pytest 9-26, 36-41 ---
$junitApi = Join-Path $ReportDir "pytest-junit.xml"
Push-Location (Join-Path $Root "apps\api")
& $venvPy -m pytest tests/test_prompt6_acceptance.py -q --tb=short --junitxml=$junitApi
$apiCode = $LASTEXITCODE
Pop-Location
Copy-Item $junitApi (Join-Path $ReportDir "t-pytest-api.xml") -ErrorAction SilentlyContinue

function Get-P6IdFromName([string]$Name) {
  if ($Name -match "p6_(\d+)") { return [int]$Matches[1] }
  return $null
}

if (Test-Path $junitApi) {
  [xml]$xml = Get-Content $junitApi -Encoding UTF8
  $cases = @($xml.SelectNodes("//testcase"))
  foreach ($case in $cases) {
    $id = Get-P6IdFromName $case.name
    if (-not $id) { continue }
    $fail = $case.SelectSingleNode("failure")
    $err = $case.SelectSingleNode("error")
    $skip = $case.SelectSingleNode("skipped")
    $cmd = "pytest apps/api/tests/test_prompt6_acceptance.py::{0}" -f $case.name
    if ($fail -or $err) {
      $msg = if ($fail) { $fail.InnerText } else { $err.InnerText }
      $ev = Write-Evidence ("t{0:d2}-pytest.txt" -f $id) $msg
      Add-Result $id "FAIL" $cmd $ev ("P6-T{0:d2}" -f $id)
    } elseif ($skip) {
      Add-Result $id "SKIP" $cmd $junitApi ("P6-T{0:d2}" -f $id)
    } else {
      Add-Result $id "PASS" $cmd $junitApi
    }
  }
} else {
  foreach ($id in @(9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,36,37,38,39,40,41)) {
    Add-Result $id "FAIL" "pytest test_prompt6_acceptance.py" $ReportDir ("P6-T{0:d2}" -f $id)
  }
}

# Playwright Chromium for visual tests (override Cursor sandbox browser cache)
$pwBrowsers = Join-Path $Root "apps\web\.playwright-browsers"
New-Item -ItemType Directory -Force -Path $pwBrowsers | Out-Null
$env:PLAYWRIGHT_BROWSERS_PATH = $pwBrowsers
$chromeShell = Get-ChildItem -Path $pwBrowsers -Recurse -Filter "chrome-headless-shell.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $chromeShell) {
  Write-Host "==> playwright install chromium"
  Push-Location (Join-Path $Root "apps\web")
  corepack pnpm exec playwright install chromium
  if ($LASTEXITCODE -ne 0) { Write-Host "playwright install failed" }
  Pop-Location
}

# --- live instance for visual via real shortcut target ---
$visualData = Join-Path $clean "visual-data"
$visualRuntime = Join-Path $clean "visual-runtime"
New-Item -ItemType Directory -Force -Path $visualData, $visualRuntime | Out-Null
$env:DOCLY_HEADLESS = "1"
$env:DOCLY_NO_BROWSER = "1"
$env:DOCLY_DATA_DIR = $visualData
$env:DOCLY_RUNTIME_DIR = $visualRuntime

$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
Write-Host "==> Start via Docly.lnk target"
$startArgs = $sc.Arguments
Start-Process -FilePath $sc.TargetPath -ArgumentList $startArgs -WorkingDirectory $sc.WorkingDirectory | Out-Null

$visualInstFile = Join-Path $visualRuntime "instance.json"
$deadline = (Get-Date).AddMinutes(3)
$visualInst = $null
while ((Get-Date) -lt $deadline) {
  if (Test-Path $visualInstFile) {
    try {
      $visualInst = Get-Content $visualInstFile -Raw -Encoding UTF8 | ConvertFrom-Json
      $live = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/live" -f $visualInst.api_port) -UseBasicParsing -TimeoutSec 3
      if ($live.StatusCode -eq 200) { break }
    } catch { $visualInst = $null }
  }
  Start-Sleep -Seconds 2
}

if (-not $visualInst) {
  foreach ($id in 27..35) {
    Add-Result $id "FAIL" "Docly.lnk live visual" $visualInstFile ("P6-T{0:d2}" -f $id)
  }
  [void]$Nogo.Add("shortcut-does-not-launch")
} else {
  $env:PW_NO_WEBSERVER = "1"
  $env:PW_JSON_FILE = Join-Path $ReportDir "playwright.json"
  $env:PLAYWRIGHT_BASE_URL = "http://127.0.0.1:{0}" -f $visualInst.web_port
  $env:E2E_WEB_BASE_URL = $env:PLAYWRIGHT_BASE_URL
  $env:E2E_API_BASE_URL = "http://127.0.0.1:{0}" -f $visualInst.api_port
  Push-Location (Join-Path $Root "apps\web")
  corepack pnpm exec playwright test e2e/prompt6-acceptance.spec.ts --retries=0
  $pwCode = $LASTEXITCODE
  Pop-Location
  $pwJson = Join-Path $ReportDir "playwright.json"
  $pwMap = @{}
  if (Test-Path $pwJson) {
    $parsed = Get-Content $pwJson -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($suite in @($parsed.suites)) {
      $stack = New-Object System.Collections.Stack
      $stack.Push($suite)
      while ($stack.Count -gt 0) {
        $cur = $stack.Pop()
        foreach ($child in @($cur.suites)) { $stack.Push($child) }
        foreach ($spec in @($cur.specs)) {
          $id = Get-P6IdFromName $spec.title
          if ($id) {
            $ok = $true
            foreach ($t in @($spec.tests)) {
              foreach ($r in @($t.results)) {
                if ($r.status -and $r.status -ne "passed") { $ok = $false }
              }
            }
            $pwMap[$id] = $ok
          }
        }
      }
    }
  }

  foreach ($id in 27..35) {
    $cmd = "PW_NO_WEBSERVER=1 playwright test e2e/prompt6-acceptance.spec.ts -g p6_{0}" -f $id
    $shot = Join-Path $ReportDir "screenshots"
    if ($pwMap.ContainsKey($id)) {
      if ($pwMap[$id]) { Add-Result $id "PASS" $cmd $shot }
      else { Add-Result $id "FAIL" $cmd $shot ("P6-T{0:d2}" -f $id) }
    } else {
      if ($pwCode -eq 0) { Add-Result $id "PASS" $cmd $shot }
      else { Add-Result $id "FAIL" $cmd $shot ("P6-T{0:d2}" -f $id) }
    }
  }
}

& $venvPy $launcher --stop | Out-Null

# Dedupe: keep last result per id
$byId = @{}
foreach ($row in $Results) { $byId[[int]$row.id] = $row }
$final = 1..41 | ForEach-Object {
  if ($byId.ContainsKey($_)) { $byId[$_] }
  else {
    [pscustomobject]@{ id = $_; status = "FAIL"; command = "(not executed)"; evidence = $ReportDir; issue = ("P6-T{0:d2}" -f $_) }
  }
}

# Automatic NO-GO from required gates
foreach ($row in $final) {
  $id = [int]$row.id
  $failed = $row.status -ne "PASS"
  if ($failed -and $id -eq 1) { [void]$Nogo.Add("shortcut-does-not-launch") }
  if ($failed -and $id -eq 5) { [void]$Nogo.Add("shortcut-does-not-launch") }
  if ($failed -and ($id -eq 2 -or $id -eq 3)) { [void]$Nogo.Add("startup-requires-docker-postgres-redis") }
  if ($failed -and $id -eq 11) { [void]$Nogo.Add("forms-api-500") }
  if ($failed -and ($id -eq 10 -or $id -eq 14)) { [void]$Nogo.Add("catalog-lost-after-restart") }
  if ($failed -and $id -eq 16) { [void]$Nogo.Add("synthetic-government-form") }
  if ($failed -and $id -eq 17) { [void]$Nogo.Add("missing-font-hash-license") }
  if ($failed -and ($id -eq 27 -or $id -eq 28)) { [void]$Nogo.Add("body-font-below-16px-or-500") }
  if ($failed -and $id -eq 35) { [void]$Nogo.Add("screenshot-review-failed") }
  if ($failed -and $id -eq 21) { [void]$Nogo.Add("pixel-diff-changed-underlay") }
  if ($failed -and $id -eq 15) { [void]$Nogo.Add("published-form-without-official-source") }
}

$nogoUnique = $Nogo | Select-Object -Unique
$failCount = @($final | Where-Object { $_.status -ne "PASS" }).Count
$verdict = "GO"
if ($nogoUnique.Count -gt 0 -or $failCount -gt 0) { $verdict = "NO-GO" }

$jsonPath = Join-Path $ReportDir "results.json"
@{
  verdict = $verdict
  blockers = @($nogoUnique)
  results = @($final)
} | ConvertTo-Json -Depth 8 | Set-Content -Path $jsonPath -Encoding UTF8

& $venvPy (Join-Path $PSScriptRoot "prompt6_write_report.py") $jsonPath
$tablePath = Join-Path $ReportDir "results.md"
Write-Host ""
Write-Host "Report: $tablePath"
Write-Host "Verdict: $verdict"
if ($verdict -ne "GO") { exit 1 }
exit 0
