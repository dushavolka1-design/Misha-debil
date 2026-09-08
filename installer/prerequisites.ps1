#Requires -Version 5.1
param([switch]$CheckOnly, [switch]$Library)
$ErrorActionPreference = 'Stop'

function Refresh-DoclyPath {
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + $env:Path
}
function Find-DoclyNode {
    $ErrorActionPreference = 'SilentlyContinue'
    $candidates = @((Join-Path $env:ProgramFiles 'nodejs\node.exe'))
    $cmd = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($cmd) { $candidates += $cmd.Source }
    foreach ($exe in ($candidates | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $exe) {
            $v = & $exe -p "Number(process.versions.node.split('.')[0]) >= 20 && process.arch === 'x64'" 2>$null
            if ($LASTEXITCODE -eq 0 -and "$v" -eq 'true') { return $exe }
        }
    }
    return $null
}
function Find-DoclyPython {
    $ErrorActionPreference = 'SilentlyContinue'
    $candidates = @()
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        foreach ($ver in @('-3.12', '-3.13', '-3')) {
            $candidates += @{ Exe = $py.Source; Args = @($ver) }
        }
    }
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notmatch '\\WindowsApps\\') {
        $candidates += @{ Exe = $cmd.Source; Args = @() }
    }
    foreach ($pattern in @("$env:LOCALAPPDATA\Programs\Python\Python*\python.exe", "$env:ProgramFiles\Python*\python.exe")) {
        foreach ($item in (Get-Item $pattern -ErrorAction SilentlyContinue)) {
            $candidates += @{ Exe = $item.FullName; Args = @() }
        }
    }
    foreach ($c in $candidates) {
        $out = @(& $c.Exe @($c.Args + @('-c', "import sys,struct; assert sys.version_info >= (3,12) and struct.calcsize('P')==8; print(sys.executable)")) 2>$null)
        if ($LASTEXITCODE -eq 0 -and $out.Count -gt 0 -and (Test-Path -LiteralPath ([string]$out[-1]))) {
            return [string]$out[-1]
        }
    }
    return $null
}
function Assert-DoclyPrerequisites([bool]$Interactive) {
    if (-not [Environment]::Is64BitOperatingSystem -or [Environment]::OSVersion.Version.Major -lt 10 -or $env:PROCESSOR_ARCHITECTURE -ne 'AMD64') {
        throw 'Требуется Windows 10/11 x64 и 64-разрядный PowerShell 5.1 или новее.'
    }
    Refresh-DoclyPath
    foreach ($dep in @(
        @{ Name = 'Node.js 20+ x64'; Id = 'OpenJS.NodeJS.LTS'; Url = 'https://nodejs.org/en/download'; Find = { Find-DoclyNode } },
        @{ Name = 'Python 3.12+ x64'; Id = 'Python.Python.3.12'; Url = 'https://www.python.org/downloads/windows/'; Find = { Find-DoclyPython } }
    )) {
        if (& $dep.Find) { continue }
        if (-not $Interactive) { throw "Не найден $($dep.Name). Установите его и повторите запуск." }
        Add-Type -AssemblyName System.Windows.Forms
        $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
        if ($winget) {
            $answer = [Windows.Forms.MessageBox]::Show("Не найден $($dep.Name). Установить автоматически через winget? Может потребоваться подтверждение Windows.", 'Docly', 'YesNo', 'Question')
            if ($answer -ne 'Yes') { throw "Установите $($dep.Name) и повторите запуск." }
            & $winget.Source install --id $dep.Id --exact --source winget --architecture x64 --accept-package-agreements --accept-source-agreements --disable-interactivity
            $code = $LASTEXITCODE
            Refresh-DoclyPath
            if (-not (& $dep.Find)) {
                throw "Установка $($dep.Name) не завершена (код $code). Перезапустите установщик после установки зависимости."
            }
        } else {
            [Windows.Forms.MessageBox]::Show("Не найден $($dep.Name), а winget недоступен. Откроется официальный сайт. Установите x64-версию и повторите запуск установщика.", 'Docly', 'OK', 'Information') | Out-Null
            Start-Process $dep.Url
            throw "Установите $($dep.Name) с официального сайта и повторите запуск."
        }
    }
}
if (-not $Library) {
    try { Assert-DoclyPrerequisites (-not $CheckOnly); exit 0 }
    catch {
        Write-Host $_.Exception.Message
        if (-not $CheckOnly) {
            Add-Type -AssemblyName System.Windows.Forms
            [Windows.Forms.MessageBox]::Show($_.Exception.Message, 'Docly', 'OK', 'Error') | Out-Null
        }
        exit 1
    }
}
