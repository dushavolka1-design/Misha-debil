# Last Windows installer CI result

Source commit: eaec1824e333e63ca0abd73808a08914761b59c0
Build: success
Smoke: failure
Release publication: skipped
Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34257846657

A generated EXE alone is not proof that first launch passed.

## Build metadata
```json
{
    "sha256":  "b0d59011d2fb31a8f3488b07b2357cf80ed1afc2aa98d1a2b2844f4071da5e20",
    "sourceCommit":  "eaec1824e333e63ca0abd73808a08914761b59c0",
    "file":  "Docly-Setup-x64.exe",
    "bytes":  3041958
}

```

## Automated checks
```text
PASS: clean default install directory
PASS: setup exit 0
PASS: installed payload
PASS: no .git in payload
PASS: no real .env in payload
PASS: no prebuilt venv in payload
PASS: no node_modules in payload
PASS: shortcut C:\Users\runneradmin\Desktop\Docly.lnk
PASS: shortcut delegates to bootstrap
PASS: shortcut executable exists
PASS: shortcut working directory
PASS: shortcut C:\Users\runneradmin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Docly\Docly.lnk
PASS: shortcut delegates to bootstrap
PASS: shortcut executable exists
PASS: shortcut working directory
PASS: registered in installed programs
FAIL: FAIL: first-run bootstrap and launcher

```

## Diagnostic tail: install.log
```text
2026-09-08 17:35:17.161   Successfully installed the file.
2026-09-08 17:35:17.161   -- File entry --
2026-09-08 17:35:17.161   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\install-shortcuts.vbs
2026-09-08 17:35:17.161   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.161   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\prompt6_write_report.py
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\run-prompt6-acceptance.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\run-prompt8-verification.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\setup-desktop.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\setup-portable-db.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\start-dar-silent.vbs
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\start-dar.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\test-launcher.ps1
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:35:06.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Successfully installed the file.
2026-09-08 17:35:17.177   -- File entry --
2026-09-08 17:35:17.177   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\dar-icon.ico
2026-09-08 17:35:17.177   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.177   Installing the file.
2026-09-08 17:35:17.177   Creating directory: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets
2026-09-08 17:35:17.192   Successfully installed the file.
2026-09-08 17:35:17.192   -- File entry --
2026-09-08 17:35:17.192   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-icon.ico
2026-09-08 17:35:17.192   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.192   Installing the file.
2026-09-08 17:35:17.192   Successfully installed the file.
2026-09-08 17:35:17.192   -- File entry --
2026-09-08 17:35:17.192   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-logo.png
2026-09-08 17:35:17.192   Time stamp of our file: 2026-09-08 17:34:56.000
2026-09-08 17:35:17.192   Installing the file.
2026-09-08 17:35:17.192   Successfully installed the file.
2026-09-08 17:35:17.192   -- Icon entry --
2026-09-08 17:35:17.192   Dest filename: C:\Users\runneradmin\Desktop\Docly.lnk
2026-09-08 17:35:17.192   Creating the icon.
2026-09-08 17:35:17.693   Successfully created the icon.
2026-09-08 17:35:17.709   -- Icon entry --
2026-09-08 17:35:17.709   Dest filename: C:\Users\runneradmin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Docly\Docly.lnk
2026-09-08 17:35:17.709   Creating directory: C:\Users\runneradmin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Docly
2026-09-08 17:35:17.709   Creating the icon.
2026-09-08 17:35:17.771   Successfully created the icon.
2026-09-08 17:35:17.771   Saving uninstall information.
2026-09-08 17:35:17.771   Creating new uninstall key: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Uninstall\{86D10F83-C1C7-4DD9-9B3C-0A2268F7E97D}_is1
2026-09-08 17:35:17.771   Writing uninstall key values.
2026-09-08 17:35:17.771   Detected previous administrative 64-bit install? No
2026-09-08 17:35:17.771   Detected previous administrative 32-bit install? No
2026-09-08 17:35:17.787   Installation process succeeded.
2026-09-08 17:35:17.787   Need to restart Windows? No
2026-09-08 17:35:17.787   Deinitializing Setup.
2026-09-08 17:35:17.787   Log closed.
```

## Diagnostic tail: installer-bootstrap.log
```text
**********************
Windows PowerShell transcript start
Start time: 20260908173519
Username: runnervmy4vqd\runneradmin
RunAs User: runnervmy4vqd\runneradmin
Configuration Name: 
Machine: runnervmy4vqd (Microsoft Windows NT 10.0.20348.0)
Host Application: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\runneradmin\AppData\Local\Programs\Docly\installer\first-run.ps1 -Headless
Process ID: 6020
PSVersion: 5.1.20348.5499
PSEdition: Desktop
PSCompatibleVersions: 1.0, 2.0, 3.0, 4.0, 5.0, 5.1.20348.5499
BuildVersion: 10.0.20348.5499
CLRVersion: 4.0.30319.42000
WSManStackVersion: 3.0
PSRemotingProtocolVersion: 2.3
SerializationVersion: 1.1.0.1
**********************
Первый запуск Docly: загрузка зависимостей и сборка интерфейса. Требуется интернет; это может занять несколько минут.






PS>TerminatingError(): "Ошибка выполнения C:\Program Files\nodejs\node.exe (код 1). См. журнал подготовки."
Не удалось подготовить Docly: Ошибка выполнения C:\Program Files\nodejs\node.exe (код 1). См. журнал подготовки.
Журнал: C:\Users\runneradmin\AppData\Local\Programs\Docly\artifacts\local-run\installer-bootstrap.log
Закройте другой запуск Docly, проверьте интернет и повторите запуск ярлыка.
**********************
Windows PowerShell transcript end
End time: 20260908173749
**********************
```