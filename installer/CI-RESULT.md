# Last Windows installer CI result

Source commit: cc539e25d14c48f0896756d8b2711f7df29cba8a
Build: success
Smoke: failure
Release publication: skipped
Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258269841

A generated EXE alone is not proof that first launch passed.

## Build metadata
```json
{
    "sha256":  "25b9f64b1bdcf69a4bc3ff82880259062e3c7a163c074a6f52ce1c29aaead128",
    "sourceCommit":  "cc539e25d14c48f0896756d8b2711f7df29cba8a",
    "file":  "Docly-Setup-x64.exe",
    "bytes":  3052350
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
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\install-shortcuts.vbs
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\prompt6_write_report.py
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\run-prompt6-acceptance.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\run-prompt8-verification.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\setup-desktop.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\setup-portable-db.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\start-dar-silent.vbs
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\start-dar.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.677   Successfully installed the file.
2026-09-08 17:39:05.677   -- File entry --
2026-09-08 17:39:05.677   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\test-launcher.ps1
2026-09-08 17:39:05.677   Time stamp of our file: 2026-09-08 17:38:42.000
2026-09-08 17:39:05.677   Installing the file.
2026-09-08 17:39:05.693   Successfully installed the file.
2026-09-08 17:39:05.693   -- File entry --
2026-09-08 17:39:05.693   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\dar-icon.ico
2026-09-08 17:39:05.693   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.693   Installing the file.
2026-09-08 17:39:05.693   Creating directory: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets
2026-09-08 17:39:05.693   Successfully installed the file.
2026-09-08 17:39:05.693   -- File entry --
2026-09-08 17:39:05.693   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-icon.ico
2026-09-08 17:39:05.693   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.693   Installing the file.
2026-09-08 17:39:05.693   Successfully installed the file.
2026-09-08 17:39:05.693   -- File entry --
2026-09-08 17:39:05.693   Dest filename: C:\Users\runneradmin\AppData\Local\Programs\Docly\scripts\windows\assets\docly-logo.png
2026-09-08 17:39:05.693   Time stamp of our file: 2026-09-08 17:38:10.000
2026-09-08 17:39:05.693   Installing the file.
2026-09-08 17:39:05.693   Successfully installed the file.
2026-09-08 17:39:05.693   -- Icon entry --
2026-09-08 17:39:05.693   Dest filename: C:\Users\runneradmin\Desktop\Docly.lnk
2026-09-08 17:39:05.693   Creating the icon.
2026-09-08 17:39:09.156   Successfully created the icon.
2026-09-08 17:39:09.156   -- Icon entry --
2026-09-08 17:39:09.156   Dest filename: C:\Users\runneradmin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Docly\Docly.lnk
2026-09-08 17:39:09.156   Creating directory: C:\Users\runneradmin\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Docly
2026-09-08 17:39:09.172   Creating the icon.
2026-09-08 17:39:09.219   Successfully created the icon.
2026-09-08 17:39:09.219   Saving uninstall information.
2026-09-08 17:39:09.219   Creating new uninstall key: HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Uninstall\{86D10F83-C1C7-4DD9-9B3C-0A2268F7E97D}_is1
2026-09-08 17:39:09.219   Writing uninstall key values.
2026-09-08 17:39:09.219   Detected previous administrative 64-bit install? No
2026-09-08 17:39:09.219   Detected previous administrative 32-bit install? No
2026-09-08 17:39:09.234   Installation process succeeded.
2026-09-08 17:39:09.234   Need to restart Windows? No
2026-09-08 17:39:09.250   Deinitializing Setup.
2026-09-08 17:39:09.250   Log closed.
```

## Diagnostic tail: api.err.log
```text
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\.venv\Lib\site-packages\fastapi\routing.py", line 240, in merged_lifespan
    async with original_context(app) as maybe_original_state:
               ^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\contextlib.py", line 210, in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\app\main.py", line 100, in lifespan
    source_registry = SourceRegistry(fetch_fn=guarded_httpx_fetch)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\app\services\sources\registry.py", line 150, in __init__
    self.cfg = allowlist or load_allowlist()
                            ^^^^^^^^^^^^^^^^
  File "C:\Users\runneradmin\AppData\Local\Programs\Docly\apps\api\app\services\sources\url_policy.py", line 54, in load_allowlist
    data = json.loads(p.read_text(encoding="utf-8"))
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\pathlib.py", line 1027, in read_text
    with self.open(mode='r', encoding=encoding, errors=errors) as f:
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\hostedtoolcache\windows\Python\3.12.10\x64\Lib\pathlib.py", line 1013, in open
    return io.open(self, mode, buffering, encoding, errors, newline)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\runneradmin\\AppData\\Local\\Programs\\Docly\\sources\\allowlist.json'

ERROR:    Application startup failed. Exiting.
```

## Diagnostic tail: api.out.log
```text

```

## Diagnostic tail: installer-bootstrap.log
```text
**********************
Windows PowerShell transcript start
Start time: 20260908173911
Username: runnervmy4vqd\runneradmin
RunAs User: runnervmy4vqd\runneradmin
Configuration Name: 
Machine: runnervmy4vqd (Microsoft Windows NT 10.0.20348.0)
Host Application: C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\runneradmin\AppData\Local\Programs\Docly\installer\first-run.ps1 -Headless
Process ID: 5112
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








**********************
Windows PowerShell transcript end
End time: 20260908174156
**********************
```