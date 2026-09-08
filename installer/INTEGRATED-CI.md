# Integrated Docly Windows result

Source: 183cad0d86760445799f24b0dd914d4e528936f4
Integration: success
Regressions: success
Build: success
Smoke: success
Publication: success
Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34266940257
Release: https://github.com/dushavolka1-design/Misha-debil/releases/tag/docly-integrated-20260908.3.1

Previous CI-RESULT.md describes the OLD installer release, not this integration.

## release/build-info.json
```text
{
    "sha256":  "6acbc851855761527fa088f9c0e6f317face84682a305462ec7f511f4b56c088",
    "sourceCommit":  "183cad0d86760445799f24b0dd914d4e528936f4",
    "file":  "Docly-Setup-x64.exe",
    "bytes":  3082080
}

```

## release/smoke-results.txt
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