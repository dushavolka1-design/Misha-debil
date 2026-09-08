# Last Windows installer CI result

Source commit: 47873cda75018ebc3c58bb78f138ce60e06308e4
Build: success
Smoke: success
Release publication: success
Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34258968767

A generated EXE alone is not proof that first launch passed.

## Build metadata
```json
{
    "sha256":  "936ceeb7b6a5bf652f09d7fd80e1e5eaa3ac3142240557ccae112723f845c549",
    "sourceCommit":  "47873cda75018ebc3c58bb78f138ce60e06308e4",
    "file":  "Docly-Setup-x64.exe",
    "bytes":  3053048
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
PASS: first-run bootstrap and launcher
PASS: created Python venv
PASS: production Next.js build
PASS: random session secret
PASS: local fake providers allowed
PASS: existing desktop SQLite migration
PASS: default 8000/3000 ports
PASS: HTTP 200 http://127.0.0.1:8000/live
PASS: HTTP 200 http://127.0.0.1:8000/ready
PASS: HTTP 200 http://127.0.0.1:3000/app/analyzer
PASS: second launch
PASS: second launch reuses processes
PASS: second launch preserves secret
PASS: stop existing launcher
PASS: API stopped
PASS: Web stopped
PASS: setup exit 0
PASS: reinstall preserves .env
PASS: reinstall preserves user database
PASS: setup exit 0
PASS: removed installed-programs registration
PASS: removed both shortcuts
PASS: removed installed launcher
PASS: removed generated venv
PASS: uninstall preserves user data
PASS: uninstall preserves local configuration

```
Release: https://github.com/dushavolka1-design/Misha-debil/releases/tag/docly-windows-0.1.0-ci.5.1