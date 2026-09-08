#Requires -Version 5.1
# Destructive only inside the fresh installation on an ephemeral CI runner.
param([Parameter(Mandatory=$true)][string]$SetupExe)
$ErrorActionPreference = 'Stop'
$Root = Join-Path $env:LOCALAPPDATA 'Programs\Docly'
$ReportDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'release'
$Checks = New-Object Collections.Generic.List[string]
function Check([bool]$Ok, [string]$Name) {
    if (-not $Ok) { throw "FAIL: $Name" }
    $Checks.Add("PASS: $Name"); Write-Host "PASS: $Name"
}
function Run-Setup([string]$Exe, [string[]]$Arguments) {
    $p = Start-Process -FilePath $Exe -ArgumentList $Arguments -PassThru -Wait
    Check ($p.ExitCode -eq 0) "setup exit $($p.ExitCode)"
}
$py = Join-Path $Root 'apps\api\.venv\Scripts\python.exe'
$launcher = Join-Path $Root 'scripts\windows\docly_launcher.py'
$env:DOCLY_HEADLESS = '1'
$env:DOCLY_NO_BROWSER = '1'
$env:DOCLY_DATA_DIR = Join-Path $env:TEMP ('Docly smoke data ' + [guid]::NewGuid().ToString('N'))
$env:DOCLY_RUNTIME_DIR = Join-Path $env:DOCLY_DATA_DIR 'runtime'
try {
    Check (-not (Test-Path $Root)) 'clean default install directory'
    Run-Setup $SetupExe @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', ('/LOG="' + (Join-Path $ReportDir 'install.log') + '"'))
    Check (Test-Path $launcher) 'installed payload'
    Check (-not (Test-Path (Join-Path $Root '.git'))) 'no .git in payload'
    Check (-not (Test-Path (Join-Path $Root '.env'))) 'no real .env in payload'
    Check (-not (Test-Path $py)) 'no prebuilt venv in payload'
    Check (-not (Test-Path (Join-Path $Root 'node_modules'))) 'no node_modules in payload'
    $desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Docly.lnk'
    $start = Join-Path ([Environment]::GetFolderPath('Programs')) 'Docly\Docly.lnk'
    foreach ($link in @($desktop, $start)) {
        Check (Test-Path $link) "shortcut $link"
        $sc = (New-Object -ComObject WScript.Shell).CreateShortcut($link)
        Check ($sc.Arguments -like '*installer\first-run.ps1*') 'shortcut delegates to bootstrap'
        Check (Test-Path $sc.TargetPath) 'shortcut executable exists'
        Check ($sc.WorkingDirectory.TrimEnd('\') -eq $Root) 'shortcut working directory'
    }
    $reg = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{86D10F83-C1C7-4DD9-9B3C-0A2268F7E97D}_is1'
    Check (Test-Path $reg) 'registered in installed programs'
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'installer\first-run.ps1') -Headless
    Check ($LASTEXITCODE -eq 0) 'first-run bootstrap and launcher'
    Check (Test-Path $py) 'created Python venv'
    Check (Test-Path (Join-Path $Root 'apps\web\.next\BUILD_ID')) 'production Next.js build'
    $envText = [IO.File]::ReadAllText((Join-Path $Root '.env'))
    Check ($envText -match '(?m)^SESSION_SECRET=[a-f0-9]{64}\r?$') 'random session secret'
    Check ($envText -match '(?m)^ALLOW_FAKE_PROVIDERS=true\r?$') 'local fake providers allowed'
    Check (Test-Path (Join-Path $env:DOCLY_DATA_DIR 'docly.db')) 'existing desktop SQLite migration'
    $instancePath = Join-Path $env:DOCLY_RUNTIME_DIR 'instance.json'
    $inst = Get-Content $instancePath -Raw | ConvertFrom-Json
    Check ($inst.api_port -eq 8000 -and $inst.web_port -eq 3000) 'default 8000/3000 ports'
    foreach ($url in @('http://127.0.0.1:8000/live', 'http://127.0.0.1:8000/ready', 'http://127.0.0.1:3000/app/analyzer')) {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 30
        Check ($r.StatusCode -eq 200) "HTTP 200 $url"
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Root 'installer\first-run.ps1') -Headless
    Check ($LASTEXITCODE -eq 0) 'second launch'
    $again = Get-Content $instancePath -Raw | ConvertFrom-Json
    Check ($inst.api_pid -eq $again.api_pid -and $inst.web_pid -eq $again.web_pid) 'second launch reuses processes'
    Check ([IO.File]::ReadAllText((Join-Path $Root '.env')) -eq $envText) 'second launch preserves secret'
    & $py $launcher --stop
    Check ($LASTEXITCODE -eq 0) 'stop existing launcher'
    Start-Sleep -Seconds 3
    Check (-not (Get-Process -Id $inst.api_pid -ErrorAction SilentlyContinue)) 'API stopped'
    Check (-not (Get-Process -Id $inst.web_pid -ErrorAction SilentlyContinue)) 'Web stopped'
    # In-place reinstall must not package/reset runtime configuration or user data.
    $dbHash = (Get-FileHash (Join-Path $env:DOCLY_DATA_DIR 'docly.db')).Hash
    Run-Setup $SetupExe @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-')
    Check ([IO.File]::ReadAllText((Join-Path $Root '.env')) -eq $envText) 'reinstall preserves .env'
    Check ((Get-FileHash (Join-Path $env:DOCLY_DATA_DIR 'docly.db')).Hash -eq $dbHash) 'reinstall preserves user database'
    $uninstall = (Get-ItemProperty $reg).UninstallString.Trim('"')
    Run-Setup $uninstall @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/LOG="' + (Join-Path $ReportDir 'uninstall.log') + '"'))
    Check (-not (Test-Path $reg)) 'removed installed-programs registration'
    Check (-not (Test-Path $desktop) -and -not (Test-Path $start)) 'removed both shortcuts'
    Check (-not (Test-Path $launcher)) 'removed installed launcher'
    Check (-not (Test-Path $py)) 'removed generated venv'
    Check (Test-Path (Join-Path $env:DOCLY_DATA_DIR 'docly.db')) 'uninstall preserves user data'
    Check (Test-Path (Join-Path $Root '.env')) 'uninstall preserves local configuration'
} catch {
    $Checks.Add("FAIL: $($_.Exception.Message)")
    throw
} finally {
    $Checks | Set-Content (Join-Path $ReportDir 'smoke-results.txt') -Encoding UTF8
    if (Test-Path $py) { & $py $launcher --stop }
    $logs = Join-Path $Root 'artifacts\local-run'
    if (Test-Path $logs) { Copy-Item $logs (Join-Path $ReportDir 'bootstrap-logs') -Recurse -Force }
}
