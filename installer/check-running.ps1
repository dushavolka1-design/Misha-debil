#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$InstallRoot)
$ErrorActionPreference = 'Stop'
try {
    $root = [IO.Path]::GetFullPath($InstallRoot).TrimEnd('\') + '\'
    foreach ($p in (Get-CimInstance Win32_Process)) {
        if ($p.ProcessId -eq $PID -or $p.Name -notmatch '^(pythonw?|node|wscript|cscript|powershell|pwsh)\.exe$') { continue }
        if (($p.ExecutablePath -and $p.ExecutablePath.StartsWith($root, [StringComparison]::OrdinalIgnoreCase)) -or
            ($p.CommandLine -and $p.CommandLine.IndexOf($root, [StringComparison]::OrdinalIgnoreCase) -ge 0 -and $p.Name -match '^(pythonw?|node|wscript|cscript|powershell|pwsh)\.exe$')) {
            Write-Host 'Docly is running. Close its processes before changing the installation.'
            exit 1
        }
    }
    exit 0
} catch { Write-Host $_.Exception.Message; exit 2 }
