#Requires -Version 5.1
# Verify (and download if missing) OFL Noto Sans Regular. ASCII-only for Windows PowerShell 5.1.
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$Assets = Join-Path $Root "apps\api\app\services\forms\fill\assets"
$ManifestPath = Join-Path $Assets "font-manifest.json"
$Target = Join-Path $Assets "NotoSans-Regular.ttf"

if (-not (Test-Path $ManifestPath)) {
  throw "font-manifest.json not found at $ManifestPath"
}

$manifest = Get-Content $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
$expected = [string]$manifest.expected_sha256
if (-not $expected) {
  throw "font-manifest.json is missing expected_sha256"
}
$expected = $expected.ToLower()

function Get-FontHash([string]$Path) {
  return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

if (Test-Path $Target) {
  $hash = Get-FontHash $Target
  if ($hash -eq $expected) {
    Write-Host "Font verified: $Target"
    Write-Host "SHA-256: $hash"
    exit 0
  }
  Write-Host "Hash mismatch, re-downloading font"
  Remove-Item $Target -Force
}

$url = $manifest.source_url
Write-Host "Downloading $($manifest.filename) from $url"
Invoke-WebRequest -Uri $url -OutFile $Target -UseBasicParsing
$hash = Get-FontHash $Target
Write-Host "SHA-256: $hash"
if ($hash -ne $expected) {
  Remove-Item $Target -Force
  throw "Hash mismatch: expected $expected, got $hash"
}
Write-Host "Font ready: $Target"
