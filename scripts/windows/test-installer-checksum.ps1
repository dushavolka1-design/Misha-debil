#Requires -Version 5.1
# Execute only the checksum functions against synthetic bytes, never an installer.
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'test-installer.ps1'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($script, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count -ne 0) { throw "Installer test script has parse errors: $parseErrors" }
$functions = @($ast.FindAll({ param($node)
  $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -in @('Check', 'VerifiedHash')
}, $false))
if ($functions.Count -ne 2) { throw 'Expected exactly two checksum helper functions' }
foreach ($function in $functions) {
  . ([scriptblock]::Create($function.Extent.Text))
}
function ExpectFailure([scriptblock]$Action, [string]$Label) {
  $failed = $false
  try { & $Action | Out-Null } catch { $failed = $true }
  if (-not $failed) { throw "Expected rejection: $Label" }
  Write-Host "PASS: rejected $Label"
}
$root = Join-Path ([IO.Path]::GetTempPath()) ('Docly checksum fixture ' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
try {
  $exe = Join-Path $root 'synthetic-only.exe'
  [IO.File]::WriteAllBytes($exe, [byte[]](1, 2, 3, 4))
  $hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLower()
  $sidecar = "$exe.sha256"
  [IO.File]::WriteAllText($sidecar, "$hash  synthetic-only.exe`n")
  Check ((VerifiedHash $exe) -eq $hash) 'valid LF checksum accepted'
  [IO.File]::WriteAllText($sidecar, "$hash  synthetic-only.exe`r`n")
  Check ((VerifiedHash $exe) -eq $hash) 'valid CRLF checksum accepted'
  [IO.File]::WriteAllText($sidecar, "$hash  another.exe`n")
  ExpectFailure { VerifiedHash $exe } 'wrong installer name'
  [IO.File]::WriteAllText($sidecar, "not-a-checksum  synthetic-only.exe`n")
  ExpectFailure { VerifiedHash $exe } 'malformed checksum'
  [IO.File]::WriteAllText($sidecar, "$hash  synthetic-only.exe`n$hash  synthetic-only.exe`n")
  ExpectFailure { VerifiedHash $exe } 'multiple checksum records'
  [IO.File]::WriteAllText($sidecar, "$hash  synthetic-only.exe`n")
  [IO.File]::WriteAllBytes($exe, [byte[]](1, 2, 3, 5))
  ExpectFailure { VerifiedHash $exe } 'modified installer bytes'
  Remove-Item -LiteralPath $sidecar
  ExpectFailure { VerifiedHash $exe } 'missing checksum'
  [IO.File]::WriteAllText($sidecar, "$hash  synthetic-only.exe`n")
  Remove-Item -LiteralPath $exe
  ExpectFailure { VerifiedHash $exe } 'missing installer'
  Write-Host 'Checksum regressions passed: 2 positive and 6 negative cases. No installer executed.'
} finally {
  # This directory contains only synthetic bytes created above, never profile data.
  Remove-Item -LiteralPath $root -Recurse -Force
}
