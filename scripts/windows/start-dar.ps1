# Docly desktop entry (visible). Does not download PostgreSQL/Redis.
#Requires -Version 5.1
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Launcher = Join-Path $PSScriptRoot "docly_launcher.py"
$PyW = Join-Path $Root "apps\api\.venv\Scripts\pythonw.exe"
$Py = Join-Path $Root "apps\api\.venv\Scripts\python.exe"
if (Test-Path $PyW) {
  $exe = $PyW
} elseif (Test-Path $Py) {
  $exe = $Py
} else {
  $exe = (Get-Command python -ErrorAction SilentlyContinue).Source
}
if (-not $exe) {
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.MessageBox]::Show(
    "Python не найден. Запустите scripts\windows\setup-desktop.ps1",
    "Docly",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Warning
  ) | Out-Null
  exit 1
}
& $exe $Launcher
exit $LASTEXITCODE
