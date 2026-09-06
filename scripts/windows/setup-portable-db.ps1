#Requires -Version 5.1
# Portable PostgreSQL + Redis bundled with Docly (no Docker, no admin).
param(
  [switch]$Quiet
)

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

function Write-Step([string]$Message) {
  if (-not $Quiet) { Write-Host $Message }
}

$Root = Resolve-RepoRoot -StartDir (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$PortableRoot = Join-Path $Root "infra\portable"
$PgRoot = Join-Path $PortableRoot "pgsql"
$RedisRoot = Join-Path $PortableRoot "redis"
$DataRoot = Join-Path $Root "infra\.data"
$PgData = Join-Path $DataRoot "pgdata"
$RuntimeFile = Join-Path $DataRoot "docly-runtime.env"
$LogDir = Join-Path $Root "artifacts\local-run"
$PgPort = 5432
$RedisPort = 6379

New-Item -ItemType Directory -Force -Path $PortableRoot, $DataRoot, $LogDir | Out-Null

function Test-PortOpen([int]$Port) {
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $wait = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    $ok = $wait.AsyncWaitHandle.WaitOne(1500, $false)
    if ($ok -and $client.Connected) { $client.Close(); return $true }
    $client.Close()
  } catch { }
  return $false
}

function Pick-FreePort([int[]]$Candidates) {
  foreach ($port in $Candidates) {
    if (-not (Test-PortOpen $port)) { return $port }
  }
  throw "No free port in: $($Candidates -join ', ')"
}

function Save-RuntimeEnv {
  @(
    "DOCLY_PG_PORT=$PgPort"
    "DOCLY_REDIS_PORT=$RedisPort"
    "DATABASE_URL=postgresql+psycopg://dar_local:dar_local_password_change_me@127.0.0.1:${PgPort}/dar_local"
    "REDIS_URL=redis://127.0.0.1:${RedisPort}/0"
  ) | Set-Content -Path $RuntimeFile -Encoding UTF8
}

function Download-File([string]$Url, [string]$Dest) {
  if (Test-Path $Dest) { Remove-Item $Dest -Force }
  curl.exe --ssl-no-revoke -L --fail --retry 3 --retry-delay 2 -o $Dest $Url
  if ($LASTEXITCODE -ne 0 -or -not (Test-Path $Dest)) {
    throw "Download failed: $Url"
  }
  $head = Get-Content $Dest -Encoding Byte -TotalCount 2
  if ($head[0] -ne 0x50 -or $head[1] -ne 0x4B) {
    Remove-Item $Dest -Force -ErrorAction SilentlyContinue
    throw "Download is not a zip archive: $Url"
  }
}

function Ensure-PostgresBinaries {
  $pgCtl = Join-Path $PgRoot "bin\pg_ctl.exe"
  if (Test-Path $pgCtl) { return $pgCtl }

  $zipUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.6-2-windows-x64-binaries.zip"
  $zipPath = Join-Path $PortableRoot "pgsql.zip"
  Write-Step "Downloading PostgreSQL (first run, ~300 MB)..."
  Download-File -Url $zipUrl -Dest $zipPath
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  if (Test-Path $PgRoot) { Remove-Item $PgRoot -Recurse -Force }
  [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $PortableRoot)
  Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

  $extracted = Get-ChildItem $PortableRoot -Directory | Where-Object { $_.Name -like "pgsql*" } | Select-Object -First 1
  if ($extracted -and $extracted.FullName -ne $PgRoot) {
    Rename-Item $extracted.FullName "pgsql"
  }
  if (-not (Test-Path $pgCtl)) { throw "PostgreSQL binaries missing after extract" }
  return $pgCtl
}

function Ensure-RedisBinaries {
  $redisServer = Join-Path $RedisRoot "redis-server.exe"
  if (Test-Path $redisServer) { return $redisServer }

  $zipUrl = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
  $zipPath = Join-Path $PortableRoot "redis.zip"
  Write-Step "Downloading Redis..."
  Download-File -Url $zipUrl -Dest $zipPath
  if (-not (Test-Path $redisServer)) {
    New-Item -ItemType Directory -Force -Path $RedisRoot | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $RedisRoot)
  }
  Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
  if (-not (Test-Path $redisServer)) { throw "redis-server.exe missing after extract" }
  return $redisServer
}

function Initialize-PostgresCluster {
  param([string]$PgCtlPath)
  $initdb = Join-Path $PgRoot "bin\initdb.exe"
  if (Test-Path (Join-Path $PgData "PG_VERSION")) { return }

  Write-Step "Initializing database..."
  New-Item -ItemType Directory -Force -Path $PgData | Out-Null
  & $initdb -D $PgData -U postgres -A trust -E UTF8 --locale=C 2>&1 |
    Out-File (Join-Path $LogDir "pg-init.log") -Encoding UTF8
  if ($LASTEXITCODE -ne 0) { throw "initdb failed. See artifacts/local-run/pg-init.log" }
}

function Start-Postgres {
  param([string]$PgCtlPath)
  if (Test-PortOpen $PgPort) {
    $psql = Join-Path $PgRoot "bin\psql.exe"
    if (Test-Path $psql) {
      $ping = & $psql -U postgres -h 127.0.0.1 -p $PgPort -tAc "SELECT 1" 2>$null
      if ($ping -eq "1") { return }
    }
  }

  $pidFile = Join-Path $PgData "postmaster.pid"
  if (Test-Path $pidFile) {
    try {
      & $PgCtlPath -D $PgData status 2>$null | Out-Null
      if ($LASTEXITCODE -eq 0) { return }
    } catch { }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }

  Write-Step "Starting PostgreSQL on port $PgPort..."
  & $PgCtlPath -D $PgData -l (Join-Path $LogDir "pg.log") start -o "-p $PgPort" 2>&1 |
    Out-File (Join-Path $LogDir "pg-start.log") -Append -Encoding UTF8
  for ($i = 0; $i -lt 45; $i++) {
    if (Test-PortOpen $PgPort) { break }
    Start-Sleep -Seconds 1
  }
  if (-not (Test-PortOpen $PgPort)) {
    throw "PostgreSQL did not start on port $PgPort. See artifacts/local-run/pg.log"
  }
}

function Ensure-PostgresRoleAndDb {
  $psql = Join-Path $PgRoot "bin\psql.exe"
  $roleExists = & $psql -U postgres -h 127.0.0.1 -p $PgPort -tAc "SELECT 1 FROM pg_roles WHERE rolname='dar_local'" 2>$null
  if ($roleExists -ne "1") {
    & $psql -U postgres -h 127.0.0.1 -p $PgPort -c "CREATE USER dar_local WITH PASSWORD 'dar_local_password_change_me' CREATEDB;" 2>$null
  }
  $dbExists = & $psql -U postgres -h 127.0.0.1 -p $PgPort -tAc "SELECT 1 FROM pg_database WHERE datname='dar_local'" 2>$null
  if ($dbExists -ne "1") {
    & $psql -U postgres -h 127.0.0.1 -p $PgPort -c "CREATE DATABASE dar_local OWNER dar_local;" 2>$null
  }
}

function Start-Redis {
  param([string]$RedisServerPath)
  if (Test-PortOpen $RedisPort) { return }

  $marker = Join-Path $DataRoot "redis-$RedisPort.pid"
  if (Test-Path $marker) {
    $raw = Get-Content $marker -ErrorAction SilentlyContinue
    if ($raw -match '^\d+$') {
      $proc = Get-Process -Id ([int]$raw) -ErrorAction SilentlyContinue
      if ($proc) { return }
    }
  }

  Write-Step "Starting Redis on port $RedisPort..."
  $conf = Join-Path $DataRoot "redis-$RedisPort.conf"
  @(
    "bind 127.0.0.1"
    "port $RedisPort"
    "maxmemory 128mb"
    "appendonly no"
  ) | Set-Content -Path $conf -Encoding ASCII

  $proc = Start-Process -FilePath $RedisServerPath -ArgumentList $conf -WorkingDirectory $RedisRoot -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $LogDir "redis.out.log") `
    -RedirectStandardError (Join-Path $LogDir "redis.err.log") -PassThru

  if ($proc) { $proc.Id | Set-Content -Path $marker -Encoding ASCII }

  for ($i = 0; $i -lt 20; $i++) {
    if (Test-PortOpen $RedisPort) { break }
    Start-Sleep -Seconds 1
  }
  if (-not (Test-PortOpen $RedisPort)) {
    throw "Redis did not start on port $RedisPort. See artifacts/local-run/redis.err.log"
  }
}

Write-Step "Docly: starting bundled database..."

if (Test-Path $RuntimeFile) {
  Get-Content $RuntimeFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^DOCLY_PG_PORT=(\d+)$') { $PgPort = [int]$Matches[1] }
    if ($line -match '^DOCLY_REDIS_PORT=(\d+)$') { $RedisPort = [int]$Matches[1] }
  }
} else {
  $PgPort = Pick-FreePort @(5432, 15432, 25432)
  $RedisPort = Pick-FreePort @(6379, 16379, 26379)
  Save-RuntimeEnv
}

$pgCtl = Ensure-PostgresBinaries
$redisServer = Ensure-RedisBinaries
Initialize-PostgresCluster -PgCtlPath $pgCtl
Start-Postgres -PgCtlPath $pgCtl
Ensure-PostgresRoleAndDb
Start-Redis -RedisServerPath $redisServer
Save-RuntimeEnv

Write-Step "PostgreSQL: OK ($PgPort)"
Write-Step "Redis:      OK ($RedisPort)"
Write-Step "Done."
