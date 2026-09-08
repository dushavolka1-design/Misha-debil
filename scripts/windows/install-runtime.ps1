#Requires -Version 5.1
# Offline post-install setup. Does not touch Docly user data or settings.
$ErrorActionPreference = 'Stop'
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$basePy = Join-Path $Root 'runtime\python\python.exe'
$venv = Join-Path $Root 'apps\api\.venv'
$venvPy = Join-Path $venv 'Scripts\python.exe'
$env:PYTHONDONTWRITEBYTECODE = '1'
& $basePy -m venv $venv
if ($LASTEXITCODE -ne 0) { throw 'Bundled Python environment setup failed' }
& $venvPy -m pip install --no-index --upgrade --find-links (Join-Path $Root 'wheelhouse') -r (Join-Path $Root 'apps\api\requirements.txt') dar-core
if ($LASTEXITCODE -ne 0) { throw 'Offline dependency installation failed' }
& $venvPy -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed Python dependency check failed' }
exit 0
