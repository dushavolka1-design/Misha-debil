# Last Windows installer CI result

Source commit: c3c0fd833297900f6703dc8f419c01a926ab9349
Build: success
Smoke: failure
Release publication: skipped
Run: https://github.com/dushavolka1-design/Misha-debil/actions/runs/34257558249

A generated EXE alone is not proof that first launch passed.

## Build metadata
```json
{
    "sha256":  "10f86c8d703332d34133906d8669fb2c3621564b22f962bf31faa4761bb6097a",
    "sourceCommit":  "c3c0fd833297900f6703dc8f419c01a926ab9349",
    "file":  "Docly-Setup-x64.exe",
    "bytes":  3041956
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