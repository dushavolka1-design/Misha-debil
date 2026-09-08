#Requires -Version 5.1
param([string]$IsccPath)
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Stage = Join-Path $PSScriptRoot '.stage'
$Payload = Join-Path $Stage 'payload'
$Release = Join-Path $Root 'release'
if (-not [Environment]::Is64BitOperatingSystem -or $env:OS -ne 'Windows_NT') { throw 'Build on Windows x64 with Inno Setup 6.3+.' }
if (-not $IsccPath) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $IsccPath = $cmd.Source }
    else { $IsccPath = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe' }
}
if (-not (Test-Path $IsccPath)) { throw 'Install Inno Setup 6.3+ from https://jrsoftware.org/isdl.php or winget install --id JRSoftware.InnoSetup -e' }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { throw 'Git is required to stage tracked source files safely.' }
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force -Path $Payload, $Release | Out-Null
Push-Location $Root
try {
    $tracked = & git -c core.quotepath=false ls-files
    if ($LASTEXITCODE -ne 0) { throw 'git ls-files failed' }
    $rootFiles = @('package.json', 'pnpm-lock.yaml', 'pnpm-workspace.yaml', 'turbo.json', 'tsconfig.base.json', '.env.example')
    $installerFiles = @('installer/first-run.ps1', 'installer/prerequisites.ps1', 'installer/check-running.ps1', 'installer/README.md')
    $deny = '(^|/)(\.git|\.github|node_modules|\.venv|venv|artifacts|logs?|\.next|\.turbo|\.cache|\.pytest_cache|__pycache__|\.mypy_cache|\.ruff_cache|\.pnpm-store|test-results|playwright-report|coverage|tests?|__tests__|fixtures|uploads?|user[_-]?data|pgdata|redis-data|data|tmp|temp|\.stage|\.tools)(/|$)|(^|/)\.env($|\.)|\.(log|pyc|pyo|db|sqlite3?|sqlite-wal|sqlite-shm|dump|bak|tmp|pem|key|pfx|p12|rdb|aof)$|(^|/)dump\.sql$'
    $manifest = @()
    foreach ($rel in $tracked) {
        $rel = $rel.Replace('\', '/')
        $allowed = ($rootFiles -contains $rel) -or ($installerFiles -contains $rel) -or ($rel -match '^(apps/|packages/|scripts/windows/|legal/)')
        if (-not $allowed) { continue }
        if ($rel -ne '.env.example' -and $rel -match $deny) { continue }
        if ($rel -match '(^|/)(AGENTS\.md|\.DS_Store)$|\.(test|spec)\.[cm]?[jt]sx?$') { continue }
        $src = Join-Path $Root $rel
        if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { throw "Tracked file missing: $rel" }
        if ((Get-Item -LiteralPath $src).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Symlink forbidden: $rel" }
        $dest = Join-Path $Payload $rel
        New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dest
        # Windows PowerShell 5.1 needs a UTF-8 BOM for Russian text.
        if ($rel.EndsWith('.ps1')) { [IO.File]::WriteAllText($dest, [IO.File]::ReadAllText($src), (New-Object Text.UTF8Encoding($true))) }
        $manifest += $rel
    }
    # Never package a developer's .npmrc (may contain registry credentials).
    [IO.File]::WriteAllText((Join-Path $Payload '.npmrc'), "strict-peer-dependencies=false`nauto-install-peers=true`n")
    $revision = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot determine source revision' }
    [IO.File]::WriteAllText((Join-Path $Payload 'installer\build-id.txt'), [string]$revision)
    foreach ($required in @('apps/api/requirements.txt', 'apps/web/package.json', 'packages/py_dar/pyproject.toml', 'scripts/windows/docly_launcher.py', 'scripts/windows/start-dar-silent.vbs', 'scripts/windows/assets/docly-icon.ico', '.env.example', 'installer/first-run.ps1')) {
        if (-not (Test-Path (Join-Path $Payload $required))) { throw "Required payload file missing: $required" }
    }
    $manifest += @('.npmrc', 'installer/build-id.txt')
    $manifest | Sort-Object | Set-Content (Join-Path $Release 'payload-manifest.txt') -Encoding UTF8
    # Inspect the final payload, not just the input filenames.
    foreach ($file in (Get-ChildItem $Payload -File -Recurse -Force)) {
        $rel = $file.FullName.Substring($Payload.Length + 1).Replace('\', '/')
        if ($rel -ne '.env.example' -and $rel -match $deny) { throw "Forbidden payload file: $rel" }
        if ($file.Length -gt 50MB) { throw "Unexpected large source file: $rel" }
        if ($file.Extension -match '^\.(py|js|ts|tsx|json|yaml|yml|ps1|vbs|md|txt)$' -or $rel -eq '.env.example') {
            $text = [IO.File]::ReadAllText($file.FullName)
            if ($text -match '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{32,}') { throw "Possible secret in payload: $rel" }
        }
    }
    $iss = Join-Path $Stage 'docly.iss'
    [IO.File]::WriteAllText($iss, [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'docly.iss')), (New-Object Text.UTF8Encoding($true)))
    $exe = Join-Path $Release 'Docly-Setup-x64.exe'
    if (Test-Path $exe) { Remove-Item $exe -Force }
    & $IsccPath "/DPayloadDir=$Payload" "/DReleaseDir=$Release" $iss
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { throw 'Inno Setup compilation failed' }
    $hash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    "$hash  Docly-Setup-x64.exe" | Set-Content (Join-Path $Release 'Docly-Setup-x64.exe.sha256') -Encoding ASCII
    @{ file = 'Docly-Setup-x64.exe'; bytes = (Get-Item $exe).Length; sha256 = $hash; sourceCommit = [string]$revision } | ConvertTo-Json | Set-Content (Join-Path $Release 'build-info.json') -Encoding UTF8
    Write-Host "Built $exe ($((Get-Item $exe).Length) bytes)"
} finally { Pop-Location }
