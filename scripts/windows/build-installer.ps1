#Requires -Version 5.1
param(
  [ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version = '0.2.2',
  [string]$SourceRef = 'HEAD'
)
$ErrorActionPreference = 'Stop'
$env:CI = 'true'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$buildPy = Join-Path $Root 'apps\api\.venv\Scripts\python.exe'
if (-not (Test-Path $buildPy)) { throw 'Run setup-desktop.ps1 before packaging' }
function Run([string]$File, [string[]]$Arguments) {
  & $File @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$File failed: $LASTEXITCODE" }
}
Push-Location $Root
try {
  $sourceSha = git rev-parse --verify "$SourceRef^{commit}"
  if ($LASTEXITCODE -ne 0) { throw 'Invalid source commit' }
  $work = Join-Path $Root ('artifacts\installer\build-' + [guid]::NewGuid().ToString('N'))
  $stage = Join-Path $work 'payload'
  New-Item -ItemType Directory -Path $work | Out-Null
  $archive = Join-Path $work 'source.zip'
  Run 'git' @('archive', '--format=zip', "--output=$archive", $sourceSha)
  Expand-Archive -LiteralPath $archive -DestinationPath $stage
  # Current packaging tools also support building the original source revision.
  foreach ($file in @('launch-installed.vbs', 'install-runtime.ps1')) {
    Copy-Item (Join-Path $PSScriptRoot $file) (Join-Path $stage "scripts\windows\$file")
  }
  Push-Location $stage
  try {
    # Hoisted layout is used only for the distribution, not the developer checkout.
    Run 'pnpm' @('install', '--frozen-lockfile', '--node-linker=hoisted')
    $env:NEXT_PUBLIC_API_BASE_URL = 'http://127.0.0.1:8000'
    Run 'pnpm' @('--filter', '@dar/web', 'build')
    # Compile the TypeScript Next config before removing build-only dependencies.
    $configCompiler = Join-Path $stage 'compile-next-config.cjs'
    [IO.File]::WriteAllText($configCompiler, 'const fs=require("fs"),ts=require("typescript"),p="apps/web/next.config.ts";fs.writeFileSync("apps/web/next.config.mjs",ts.transpileModule(fs.readFileSync(p,"utf8"),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2020}}).outputText);fs.unlinkSync(p)')
    Run 'node' @($configCompiler)
    Remove-Item -LiteralPath $configCompiler
    Run 'pnpm' @('install', '--prod', '--frozen-lockfile', '--node-linker=hoisted')
    $wheels = Join-Path $stage 'wheelhouse'
    New-Item -ItemType Directory -Path $wheels | Out-Null
    Run 'python' @('-m', 'pip', 'wheel', '-r', 'apps/api/requirements.txt', './packages/py_dar', '--wheel-dir', $wheels)
    Run $buildPy @((Join-Path $stage 'scripts/windows/build-dar-icon.py'))
    Run 'powershell' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $stage 'scripts/windows/install-form-font.ps1'))
  } finally { Pop-Location }
  Run 'python' @((Join-Path $PSScriptRoot 'stage-runtime.py'), $stage, $Version, $sourceSha)
  $compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
  if (-not (Test-Path $compiler)) { throw 'Install Inno Setup 6 before building the installer' }
  $output = Join-Path $Root 'artifacts\installer'
  Run $compiler @("/DAppVersion=$Version", "/DPayloadDir=$stage", "/DOutputDir=$output", (Join-Path $PSScriptRoot 'docly.iss'))
  $installer = Join-Path $output "Docly-$Version-windows-x64-setup.exe"
  if (-not (Test-Path $installer)) { throw 'Installer file missing after compilation' }
  $hash = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLower()
  [IO.File]::WriteAllText("$installer.sha256", "$hash  $([IO.Path]::GetFileName($installer))`n")
  Write-Host "Installer: $installer"
  Write-Host "Source commit: $sourceSha"
} finally { Pop-Location }
