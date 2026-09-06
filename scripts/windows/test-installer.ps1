#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$OldInstaller,
      [Parameter(Mandatory=$true)][string]$NewInstaller)
$ErrorActionPreference = 'Stop'
$work = Join-Path ([IO.Path]::GetTempPath()) ("Docly acceptance's " + [char]0x414 + [guid]::NewGuid().ToString('N'))
$install = Join-Path $work 'Application'
New-Item -ItemType Directory -Path $work | Out-Null
$env:LOCALAPPDATA = Join-Path $work 'Profile Local'
$env:DOCLY_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Docly\data'
$env:DOCLY_RUNTIME_DIR = Join-Path $env:LOCALAPPDATA 'Docly\runtime'
$env:DOCLY_NO_BROWSER = '1'
$env:DOCLY_HEADLESS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
# Neither system Python nor system Node is available to the installed launcher.
$env:PATH = "$env:WINDIR\System32;$env:WINDIR"
$py = Join-Path $install 'apps\api\.venv\Scripts\python.exe'
$launcher = Join-Path $install 'scripts\windows\docly_launcher.py'
function Check([bool]$Value, [string]$Message) {
  if (-not $Value) { throw $Message }
  Write-Host "PASS: $Message"
}
function Install([string]$Exe, [string]$Label) {
  $log = Join-Path $work "$Label.log"
  $process = Start-Process -FilePath $Exe -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$install`"", "/LOG=`"$log`"") -PassThru -Wait
  Check ($process.ExitCode -eq 0) "$Label exit code"
  Check (Test-Path $py) "$Label bundled Python environment"
}
function Launch {
  $wrapper = Join-Path $install 'scripts\windows\launch-installed.vbs'
  $null = Start-Process -FilePath "$env:WINDIR\System32\wscript.exe" -ArgumentList "`"$wrapper`"" -PassThru -Wait
  $instance = Join-Path $env:DOCLY_RUNTIME_DIR 'instance.json'
  $deadline = (Get-Date).AddSeconds(120)
  while (-not (Test-Path $instance) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
  Check (Test-Path $instance) 'installed launcher started services'
  $state = Get-Content $instance -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($endpoint in @("http://127.0.0.1:$($state.api_port)/live", "http://127.0.0.1:$($state.api_port)/ready", "http://127.0.0.1:$($state.web_port)/app/analyzer")) {
    $response = Invoke-WebRequest -Uri $endpoint -UseBasicParsing -TimeoutSec 20
    Check ($response.StatusCode -eq 200) "HTTP 200: $endpoint"
  }
}
function Stop-Docly {
  & $py $launcher --stop
  Check ($LASTEXITCODE -eq 0) 'installed services stopped'
}
try {
  Install $OldInstaller 'clean-old-install'
  Launch
  Stop-Docly
  $db = Join-Path $env:DOCLY_DATA_DIR 'docly.db'
  Check (Test-Path $db) 'application created persistent SQLite database'
  & $py -c "import os,sqlite3,json; from pathlib import Path; p=Path(os.environ['DOCLY_DATA_DIR']); c=sqlite3.connect(p/'docly.db'); c.execute('CREATE TABLE installer_acceptance (value TEXT NOT NULL)'); c.execute('INSERT INTO installer_acceptance VALUES (?)', ('retained user state',)); c.commit(); c.close(); (p/'settings.json').write_text(json.dumps(dict(theme='dark')),encoding='utf-8'); (p/'objects'/'acceptance.bin').write_bytes(b'preserved document')"
  Check ($LASTEXITCODE -eq 0) 'seed persistent database, settings and document'
  $settings = Join-Path $env:DOCLY_DATA_DIR 'settings.json'
  $document = Join-Path $env:DOCLY_DATA_DIR 'objects\acceptance.bin'
  $settingsHash = (Get-FileHash $settings).Hash
  $documentHash = (Get-FileHash $document).Hash
  Install $NewInstaller 'upgrade-install'
  $version = Get-Content (Join-Path $install 'version.json') -Raw | ConvertFrom-Json
  Check ($version.version -eq '0.2.1') 'new application version installed'
  Launch
  Stop-Docly
  & $py -c "import os,sqlite3; from pathlib import Path; c=sqlite3.connect(Path(os.environ['DOCLY_DATA_DIR'])/'docly.db'); assert c.execute('SELECT value FROM installer_acceptance').fetchall()==[('retained user state',)]; assert c.execute('PRAGMA integrity_check').fetchone()==('ok',); c.close()"
  Check ($LASTEXITCODE -eq 0) 'database rows and integrity preserved through upgrade'
  Check ((Get-FileHash $settings).Hash -eq $settingsHash) 'settings preserved through upgrade'
  Check ((Get-FileHash $document).Hash -eq $documentHash) 'document preserved through upgrade'
  $databaseHash = (Get-FileHash $db).Hash
  $uninstaller = Join-Path $install 'unins000.exe'
  Check (Test-Path $uninstaller) 'registered uninstaller exists'
  $process = Start-Process $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -PassThru -Wait
  Check ($process.ExitCode -eq 0) 'uninstaller exit code'
  $deadline = (Get-Date).AddSeconds(30)
  while ((Test-Path $py) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 300 }
  Check (-not (Test-Path $py)) 'generated Python environment removed'
  Check (-not (Test-Path (Join-Path $install 'runtime\node\node.exe'))) 'bundled Node removed'
  Check ((Get-FileHash $db).Hash -eq $databaseHash) 'uninstall retained database'
  Check ((Get-FileHash $settings).Hash -eq $settingsHash) 'uninstall retained settings'
  Check ((Get-FileHash $document).Hash -eq $documentHash) 'uninstall retained document'
  $env:DOCLY_DATA_DIR = Join-Path $work 'Fresh profile\Docly\data'
  $env:DOCLY_RUNTIME_DIR = Join-Path $work 'Fresh profile\Docly\runtime'
  Check (-not (Test-Path $env:DOCLY_DATA_DIR)) 'new-version clean profile is empty'
  Install $NewInstaller 'clean-new-install'
  Launch
  Stop-Docly
  Write-Host 'Installer lifecycle acceptance passed.'
} finally {
  # Keep all evidence/data for diagnostics. Never recursively delete a profile.
  Write-Host "Acceptance evidence: $work"
}
