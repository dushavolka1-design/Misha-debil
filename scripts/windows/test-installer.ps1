#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$OldInstaller,
      [Parameter(Mandatory=$true)][string]$NewInstaller,
      [Parameter(Mandatory=$true)][ValidatePattern('^[a-fA-F0-9]{40}$')][string]$NewSourceCommit)
$ErrorActionPreference = 'Stop'
$work = Join-Path ([IO.Path]::GetTempPath()) ("Docly acceptance's " + [char]0x414 + [guid]::NewGuid().ToString('N'))
$install = Join-Path $work 'Application'
New-Item -ItemType Directory -Path $work | Out-Null
$env:LOCALAPPDATA = Join-Path $work 'Profile Local'
$env:DOCLY_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Docly\data'
$env:DOCLY_RUNTIME_DIR = Join-Path $env:LOCALAPPDATA 'Docly\Docly\runtime'
$env:DOCLY_NO_BROWSER = '1'
$env:DOCLY_HEADLESS = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
# Neither system Python nor system Node is available to the installed launcher.
$env:PATH = "$env:WINDIR\System32;$env:WINDIR'
$py = Join-Path $install 'apps\api\.venv\Scripts\python.exe'
$launcher = Join-Path $install 'scripts\windows\docly_launcher.py'
$desktopShortcut = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Docly.lnk'
$startMenuShortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Docly\Docly.lnk'
$autostartKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
function Check([bool]$Value, [string]$Message) {
  if (-not $Value) { throw $Message }
  Write-Host "PASS: $Message"
}
function VerifiedHash([string]$Exe) {
  $checksum = (Get-Content -LiteralPath "$Exe.sha256" -Raw).Trim()
  if ($checksum -notmatch '^([a-fA-F0-9]{64})  (.+)$') { throw 'Invalid installer checksum sidecar' }
  $expectedHash = $Matches[1]
  $expectedName = $Matches[2]
  Check ($expectedName -ceq [IO.Path]::GetFileName($Exe)) 'checksum sidecar names the exact installer'
  $actualHash = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash.ToLower()
  Check ($actualHash -eq $expectedHash) 'installer SHA-256 matches sidecar'
  return $actualHash
}
function Read-Autostart {
  if (-not (Test-Path -LiteralPath $autostartKey)) { return $null }
  $values = Get-ItemProperty -LiteralPath $autostartKey -ErrorAction Stop
  $property = $values.PSObject.Properties['Docly']
  if ($null -eq $property) { return $null }
  return $property.Value
}
function Check-Shortcut([string]$Path, [string]$Label) {
  Check (Test-Path -LiteralPath $Path) "$Label exists"
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($Path)
  Check ($shortcut.TargetPath -eq "$env:WINDIR\System32\wscript.exe") "$Label uses Windows script host"
  Check ($shortcut.Arguments -eq ('"' + (Join-Path $install 'scripts\windows\launch-installed.vbs') + '"')) "$Label targets installed launcher"
  Check ($shortcut.WorkingDirectory -eq $install) "$Label working directory"
}
function Install([string]$Exe, [string]$Label, [string]$ExpectedVersion, [string]$ExpectedSource, [string]$Tasks = '') {
  $log = Join-Path $work "$Label.log"
  $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$install`"", "/LOG=`"$log`"")
  # Omit /TASKS for default-choice cases; an explicit empty string tests opt-out.
  if ($PSBoundParameters.ContainsKey('Tasks')) { $arguments += "/TASKS=`"$Tasks`"" }
  $process = Start-Process -FilePath $Exe -ArgumentList $arguments -PassThru
  Check ($process.WaitForExit(600000)) "$Label completed within ten minutes"
  Check ($process.ExitCode -eq 0) "$Label exit code"
  Check (Test-Path $py) "$Label bundled Python environment"
  $version = Get-Content (Join-Path $install 'version.json') -Raw | ConvertFrom-Json
  Check ($version.version -eq $ExpectedVersion) "$Label application version $ExpectedVersion"
  Check ($version.source_commit -eq $ExpectedSource) "$Label source commit identity"
  if ($ExpectedVersion -eq '0.2.2') {
    Check-Shortcut $desktopShortcut "$Label mandatory desktop shortcut"
    if ($Tasks -eq 'startmenu,autostart') {
      Check-Shortcut $startMenuShortcut "$Label selected Start menu shortcut"
      $expectedRun = '"' + "$env:WINDIR\System32\wscript.exe" + '" "' + (Join-Path $install 'scripts\windows\launch-installed.vbs') + '"'
      Check ((Read-Autostart) -eq $expectedRun) "$Label selected per-user autostart"
    } else {
      Check ($null -eq (Read-Autostart)) "$Label autostart disabled"
      Check (-not (Test-Path -LiteralPath $startMenuShortcut)) "$Label no unselected Start menu shortcut"
    }
    Check (-not (Test-Path (Join-Path $env:DOCLY_RUNTIME_DIR 'instance.json'))) "$Label did not launch during silent setup"
  }
}
function Launch {
  $wrapper = Join-Path $install 'scripts\windows\launch-installed.vbs'
  $wrapperProcess = Start-Process -FilePath "$env:WINDIR\System32\wscript.exe" -ArgumentList "`"$wrapper`"" -PassThru
  # Wait only for the wrapper, not its long-lived API/web descendants.
  Check ($wrapperProcess.WaitForExit(15000)) 'launch wrapper exited within fifteen seconds'
  Check ($wrapperProcess.ExitCode -eq 0) 'launch wrapper exit code'
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
  $oldHash = VerifiedHash $OldInstaller
  $newHash = VerifiedHash $NewInstaller
  Install $OldInstaller 'clean-old-install' '0.2.0' '7ab48303efa92b2e52702256dcdd360c9540d273'
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
  Install $NewInstaller 'upgrade-install' '0.2.2' $NewSourceCommit
  Launch
  Stop-Docly
  Install $NewInstaller 'optional-shortcuts-install' '0.2.2' $NewSourceCommit 'startmenu,autostart'
  Install $NewInstaller 'optional-shortcuts-disable' '0.2.2' $NewSourceCommit ''
  Install $NewInstaller 'optional-shortcuts-reenable' '0.2.2' $NewSourceCommit 'startmenu,autostart'
  & $py -c "import os,sqlite3; from pathlib import Path; c=sqlite3.connect(Path(os.environ['DOCLY_DATA_DIR'])/'docly.db'); assert c.execute('SELECT value FROM installer_acceptance').fetchall()==[('retained user state',)]; assert c.execute('PRAGMA integrity_check').fetchone()==('ok',); c.close()"
  Check ($LASTEXITCODE -eq 0) 'database rows and integrity preserved through upgrade'
  Check ((Get-FileHash $settings).Hash -eq $settingsHash) 'settings preserved through upgrade'
  Check ((Get-FileHash $document).Hash -eq $documentHash) 'document preserved through upgrade'
  $databaseHash = (Get-FileHash $db).Hash
  $uninstaller = Join-Path $install 'unins000.exe'
  Check (Test-Path $uninstaller) 'registered uninstaller exists'
  $process = Start-Process $uninstaller -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') -PassThru
  Check ($process.WaitForExit(300000)) 'uninstaller completed within five minutes'
  Check ($process.ExitCode -eq 0) 'uninstaller exit code'
  $deadline = (Get-Date).AddSeconds(30)
  while ((Test-Path $py) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 300 }
  Check (-not (Test-Path $py)) 'generated Python environment removed'
  Check (-not (Test-Path (Join-Path $install 'runtime\node\node.exe'))) 'bundled Node removed'
  Check (-not (Test-Path -LiteralPath $desktopShortcut)) 'uninstall removed application desktop shortcut'
  Check (-not (Test-Path -LiteralPath $startMenuShortcut)) 'uninstall removed selected Start menu shortcut'
  Check ($null -eq (Read-Autostart)) 'uninstall removed selected autostart entry'
  Check ((Get-FileHash $db).Hash -eq $databaseHash) 'uninstall retained database'
  Check ((Get-FileHash $settings).Hash -eq $settingsHash) 'uninstall retained settings'
  Check ((Get-FileHash $document).Hash -eq $documentHash) 'uninstall retained document'
  $env:DOCLY_DATA_DIR = Join-Path $work 'Fresh profile\Docly\data'
  $env:DOCLY_RUNTIME_DIR = Join-Path $work 'Fresh profile\Docly\runtime'
  Check (-not (Test-Path $env:DOCLY_DATA_DIR)) 'new-version clean profile is empty'
  Install $NewInstaller 'clean-new-install' '0.2.2' $NewSourceCommit
  Launch
  Stop-Docly
  Check ((VerifiedHash $OldInstaller) -eq $oldHash) 'old installer unchanged throughout tests'
  Check ((VerifiedHash $NewInstaller) -eq $newHash) 'new installer unchanged throughout tests'
  Write-Host "Candidate SHA-256: $newHash"
  Write-Host 'Limited installer lifecycle passed. NOT release acceptance: rollback, PostgreSQL migration and official forms remain unverified.'
} finally {
  # Keep all evidence/data for diagnostics. Never recursively delete a profile.
  Write-Host "Acceptance evidence: $work"
}
