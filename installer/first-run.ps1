#Requires -Version 5.1
param([switch]$Headless, [switch]$PrepareOnly)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$lock = $null
$transcribing = $false
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Ошибка выполнения $Exe (код $LASTEXITCODE). См. журнал подготовки." }
}
function Set-EnvLine([string]$Text, [string]$Key, [string]$Value) {
    $pattern = '(?m)^' + [regex]::Escape($Key) + '=.*$'
    if ([regex]::IsMatch($Text, $pattern)) { return [regex]::Replace($Text, $pattern, { param($m) "$Key=$Value" }) }
    return $Text + "`r`n$Key=$Value`r`n"
}
try {
    Set-Location $Root
    . (Join-Path $PSScriptRoot 'prerequisites.ps1') -Library
    Assert-DoclyPrerequisites (-not $Headless)
    $node = Find-DoclyNode
    $python = Find-DoclyPython
    $tools = Join-Path $PSScriptRoot '.tools'
    $env:Path = (Split-Path $node) + ';' + (Split-Path $python) + ';' + $tools + ';' + $env:Path
    $logs = Join-Path $Root 'artifacts\local-run'
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $lock = [IO.File]::Open((Join-Path $PSScriptRoot 'bootstrap.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    Start-Transcript -Path (Join-Path $logs 'installer-bootstrap.log') -Append | Out-Null
    $transcribing = $true
    $envFile = Join-Path $Root '.env'
    if (-not (Test-Path $envFile)) {
        $text = [IO.File]::ReadAllText((Join-Path $Root '.env.example'))
        $bytes = New-Object byte[] 32
        $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
        try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
        $secret = ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
        foreach ($pair in @(
            @('SESSION_SECRET', $secret), @('APP_ENV', 'desktop'), @('ALLOW_FAKE_PROVIDERS', 'true'),
            @('API_HOST', '127.0.0.1'), @('API_PUBLIC_BASE_URL', 'http://127.0.0.1:8000'),
            @('WEB_ORIGIN', 'http://127.0.0.1:3000'), @('OBJECT_STORAGE_PROVIDER', 'file_object_storage'),
            @('S3_ACCESS_KEY', 'desktop'), @('S3_SECRET_KEY', 'desktop'), @('S3_ENDPOINT_URL', 'file://local'),
            @('REDIS_URL', 'redis://127.0.0.1:0/0')
        )) { $text = Set-EnvLine $text $pair[0] $pair[1] }
        # Written only on the user's computer; never included in the EXE or repository.
        [IO.File]::WriteAllText($envFile, $text, (New-Object Text.UTF8Encoding($false)))
    }
    foreach ($line in [IO.File]::ReadAllLines($envFile)) {
        if ($line -match '^([A-Za-z_][A-Za-z_0-9]*)=(.*)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process')
        }
    }
    $venvPy = Join-Path $Root 'apps\api\.venv\Scripts\python.exe'
    $buildId = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'build-id.txt')).Trim()
    $marker = Join-Path $PSScriptRoot 'prepared.txt'
    $prepared = (Test-Path $marker) -and ([IO.File]::ReadAllText($marker).Trim() -eq $buildId)
    if (-not $prepared -or -not (Test-Path $venvPy) -or -not (Test-Path (Join-Path $Root 'apps\web\.next\BUILD_ID'))) {
        Write-Host 'Первый запуск Docly: загрузка зависимостей и сборка интерфейса. Требуется интернет; это может занять несколько минут.'
        if (Test-Path $marker) { Remove-Item $marker -Force }
        if (-not (Test-Path $venvPy)) { Invoke-Checked $python @('-m', 'venv', (Join-Path $Root 'apps\api\.venv')) }
        Invoke-Checked $venvPy @('-m', 'pip', 'install', '-r', (Join-Path $Root 'apps\api\requirements.txt'))
        Invoke-Checked $venvPy @('-m', 'pip', 'install', '-e', (Join-Path $Root 'packages\py_dar'))
        $npm = Join-Path (Split-Path $node) 'npm.cmd'
        if (-not (Test-Path $npm)) { throw 'В установке Node.js отсутствует npm. Переустановите Node.js с официального сайта.' }
        New-Item -ItemType Directory -Force -Path $tools | Out-Null
        Invoke-Checked $npm @('install', '--prefix', $tools, '--no-audit', '--no-fund', 'pnpm@9.15.9')
        $pnpm = Join-Path $tools 'node_modules\pnpm\bin\pnpm.cjs'
        Invoke-Checked $node @($pnpm, 'install', '--frozen-lockfile')
        $env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8000'
        Invoke-Checked $node @($pnpm, '--filter', '@dar/web', 'build')
        Invoke-Checked $venvPy @((Join-Path $Root 'scripts\windows\build-dar-icon.py'))
        Invoke-Checked 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $Root 'scripts\windows\install-form-font.ps1'))
        [IO.File]::WriteAllText($marker, $buildId)
    }
    Stop-Transcript | Out-Null
    $transcribing = $false
    $lock.Dispose(); $lock = $null
    if ($PrepareOnly) { exit 0 }
    if ($Headless) {
        Invoke-Checked $venvPy @((Join-Path $Root 'scripts\windows\docly_launcher.py'), '--headless')
    } else {
        # Existing visible splash, existing product launcher; no replacement UI.
        & wscript.exe (Join-Path $Root 'scripts\windows\start-dar-silent.vbs')
    }
    exit 0
} catch {
    $message = "Не удалось подготовить Docly: $($_.Exception.Message)`r`nЖурнал: $Root\artifacts\local-run\installer-bootstrap.log`r`nЗакройте другой запуск Docly, проверьте интернет и повторите запуск ярлыка."
    Write-Host $message
    if (-not $Headless) {
        Add-Type -AssemblyName System.Windows.Forms
        [Windows.Forms.MessageBox]::Show($message, 'Docly', 'OK', 'Error') | Out-Null
    }
    exit 1
} finally {
    if ($transcribing) { Stop-Transcript | Out-Null }
    if ($lock) { $lock.Dispose() }
}
