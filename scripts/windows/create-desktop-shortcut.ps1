#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$venvPy = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
if (Test-Path $venvPy) {
  & $venvPy (Join-Path $PSScriptRoot "build-dar-icon.py")
} else {
  python (Join-Path $PSScriptRoot "build-dar-icon.py")
}
if (-not (Test-Path (Join-Path $PSScriptRoot "assets\docly-icon.ico"))) {
  throw "docly-icon.ico was not created"
}
cscript //Nologo (Join-Path $PSScriptRoot "install-shortcuts.vbs")
$desktop = [Environment]::GetFolderPath("Desktop")
$lnk = Join-Path $desktop "Docly.lnk"
if (-not (Test-Path $lnk)) { throw "Docly.lnk missing on Desktop" }
$sc = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$iconFile = $sc.IconLocation.Split(",")[0]
if (-not (Test-Path $sc.TargetPath)) { throw "Shortcut target missing: $($sc.TargetPath)" }
if ($sc.Arguments -notmatch "docly_launcher.py") { throw "Shortcut args must point to docly_launcher.py" }
if (-not (Test-Path $sc.WorkingDirectory)) { throw "WorkingDirectory missing" }
if (-not (Test-Path $iconFile)) { throw "Icon missing: $iconFile" }
Write-Host "Shortcut smoke OK: $lnk"
