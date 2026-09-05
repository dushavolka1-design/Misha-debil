#Requires -Version 5.1
# Install PostgreSQL + Redis for Windows (no Docker / no virtualization).
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

function Test-PortOpen([int]$Port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $wait = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    $ok = $wait.AsyncWaitHandle.WaitOne(2000, $false)
    if ($ok -and $client.Connected) { $client.Close(); return $true }
    $client.Close()
  } catch { }
  return $false
}

function Ensure-Winget {
  if (Get-Command winget -ErrorAction SilentlyContinue) { return }
  throw "winget not found. Install App Installer from Microsoft Store."
}

Write-Host "Docly: installing local PostgreSQL and Redis (no Docker)..."

Ensure-Winget

if (-not (Test-PortOpen 5432)) {
  Write-Host "Installing PostgreSQL 17..."
  winget install --id PostgreSQL.PostgreSQL.17 --accept-package-agreements --accept-source-agreements --silent `
    --override "--mode unattended --superpassword dar_local_password_change_me --serverport 5432"
  foreach ($name in @("postgresql-x64-17", "postgresql-x64-16", "postgresql-x64-18")) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($svc) {
      if ($svc.Status -ne "Running") { Start-Service $name }
      break
    }
  }
  Start-Sleep -Seconds 5
}

if (-not (Test-PortOpen 6379)) {
  Write-Host "Installing Redis..."
  winget install --id Redis.Redis --accept-package-agreements --accept-source-agreements --silent
  foreach ($name in @("Redis", "redis")) {
    $svc = Get-Service -Name $name -ErrorAction SilentlyContinue
    if ($svc) {
      if ($svc.Status -ne "Running") { Start-Service $name }
      break
    }
  }
  Start-Sleep -Seconds 3
}

$pgBin = @(
  "C:\Program Files\PostgreSQL\17\bin\psql.exe",
  "C:\Program Files\PostgreSQL\16\bin\psql.exe",
  "C:\Program Files\PostgreSQL\18\bin\psql.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($pgBin -and (Test-PortOpen 5432)) {
  $env:PGPASSWORD = "dar_local_password_change_me"
  & $pgBin -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_roles WHERE rolname='dar_local'" 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { $env:PGPASSWORD = $null }
  $roleExists = & $pgBin -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_roles WHERE rolname='dar_local'" 2>$null
  if ($roleExists -ne "1") {
    & $pgBin -U postgres -h 127.0.0.1 -p 5432 -c "CREATE USER dar_local WITH PASSWORD 'dar_local_password_change_me' CREATEDB;" 2>$null
  }
  $dbExists = & $pgBin -U postgres -h 127.0.0.1 -p 5432 -tAc "SELECT 1 FROM pg_database WHERE datname='dar_local'" 2>$null
  if ($dbExists -ne "1") {
    & $pgBin -U postgres -h 127.0.0.1 -p 5432 -c "CREATE DATABASE dar_local OWNER dar_local;" 2>$null
  }
  $env:PGPASSWORD = $null
}

$pgOk = Test-PortOpen 5432
$redisOk = Test-PortOpen 6379
Write-Host "PostgreSQL (5432): $(if ($pgOk) { 'OK' } else { 'NOT RUNNING' })"
Write-Host "Redis (6379):      $(if ($redisOk) { 'OK' } else { 'NOT RUNNING' })"

if (-not $pgOk -or -not $redisOk) {
  Write-Host ""
  Write-Host "Some services did not start. Reboot and run this script again as Administrator."
  exit 1
}

Write-Host ""
Write-Host "Done. Launch Docly from the desktop shortcut."
