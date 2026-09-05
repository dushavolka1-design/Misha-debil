# -*- coding: utf-8 -*-
"""Visible Docly desktop launcher. No Docker, no PostgreSQL/Redis download."""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_DIR = ROOT / "apps" / "api"
WEB_DIR = ROOT / "apps" / "web"
PY_DAR = ROOT / "packages" / "py_dar" / "src"
LOG_DIR = ROOT / "artifacts" / "local-run"
ICON_ICO = ROOT / "scripts" / "windows" / "assets" / "docly-icon.ico"
LOGO_PNG = ROOT / "scripts" / "windows" / "assets" / "docly-logo.png"
CREATE_NO_WINDOW = 0x08000000

sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(PY_DAR))


def _runtime_dir() -> Path:
    override = os.environ.get("DOCLY_RUNTIME_DIR")
    if override:
        return Path(override)
    return Path(os.environ.get("LOCALAPPDATA") or ROOT) / "Docly" / "runtime"


def _data_dir() -> Path:
    override = os.environ.get("DOCLY_DATA_DIR")
    if override:
        return Path(override)
    return Path(os.environ.get("LOCALAPPDATA") or ROOT) / "Docly" / "data"


def _lock_path() -> Path:
    return _runtime_dir() / "launcher.lock"


def _instance_path() -> Path:
    return _runtime_dir() / "instance.json"


def _venv_python() -> Path:
    return API_DIR / ".venv" / "Scripts" / "python.exe"


def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _http_json(url: str, timeout: float = 2.0) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes

        SYNCHRONIZE = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _popen_hidden(args: list[str], **kwargs) -> subprocess.Popen:
    extra: dict = {}
    if sys.platform == "win32":
        extra["creationflags"] = CREATE_NO_WINDOW
    extra.update(kwargs)
    return subprocess.Popen(args, **extra)


def _check_form_font() -> None:
    import hashlib

    assets = API_DIR / "app" / "services" / "forms" / "fill" / "assets"
    manifest_path = assets / "font-manifest.json"
    if not manifest_path.is_file():
        raise LaunchError("Нет манифеста шрифта форм", str(manifest_path))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    filename = str(manifest.get("filename") or "NotoSans-Regular.ttf")
    expected = str(manifest.get("expected_sha256") or "").strip().lower()
    ttf = assets / filename
    license_path = assets / str(manifest.get("license_file") or "LICENSE")
    if not expected:
        raise LaunchError("Не зафиксирован SHA-256 шрифта форм", str(manifest_path))
    if not ttf.is_file():
        raise LaunchError(
            "Нет шрифта для заполнения форм",
            "В дистрибутиве должен быть Noto Sans (OFL).\n"
            f"{ttf}\nЗапустите scripts\\windows\\install-form-font.ps1",
        )
    actual = hashlib.sha256(ttf.read_bytes()).hexdigest().lower()
    if actual != expected:
        raise LaunchError(
            "Повреждён шрифт форм",
            "Контрольная сумма Noto Sans не совпадает с манифестом.\n"
            f"Ожидалось {expected}\nПолучено {actual}",
        )
    if not license_path.is_file():
        raise LaunchError("Нет лицензии шрифта форм", str(license_path))


class LaunchError(Exception):
    def __init__(self, title: str, details: str) -> None:
        super().__init__(title)
        self.title = title
        self.details = details


class DoclyLauncher:
    def __init__(self) -> None:
        self.log_lines: list[str] = []
        self.children: list[subprocess.Popen] = []
        self._lock_fh = None
        self.token = ""
        self.api_port = 8000
        self.web_port = 3000
        self.on_status = lambda _stage, _pct, _msg: None

    def log(self, message: str) -> None:
        line = time.strftime("%H:%M:%S ") + message
        self.log_lines.append(line)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "launcher.log").open("a", encoding="utf-8") as fh:
            fh.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + message + "\n")

    def diagnostics(self) -> str:
        return "\n".join(
            [
                "Docly diagnostics",
                f"root={ROOT}",
                f"data={_data_dir()}",
                f"api_port={self.api_port}",
                f"web_port={self.web_port}",
                *self.log_lines[-80:],
            ]
        )

    def acquire_lock(self) -> str | None:
        runtime = _runtime_dir()
        runtime.mkdir(parents=True, exist_ok=True)
        lock_path = _lock_path()
        self._lock_fh = open(lock_path, "a+b")
        self._lock_fh.seek(0)
        if self._lock_fh.read(1) == b"":
            self._lock_fh.write(b"0")
            self._lock_fh.flush()
        self._lock_fh.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(self._lock_fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self._lock_fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock_fh.close()
            self._lock_fh = None
            return "busy"
        self._lock_fh.seek(0)
        self._lock_fh.truncate()
        self._lock_fh.write(str(os.getpid()).encode("ascii"))
        self._lock_fh.flush()
        return None

    def release_lock(self) -> None:
        if self._lock_fh is None:
            return
        try:
            self._lock_fh.seek(0)
            if sys.platform == "win32":
                import msvcrt

                try:
                    msvcrt.locking(self._lock_fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            self._lock_fh.close()
        except OSError:
            pass
        self._lock_fh = None

    def our_api_running(self, port: int, token: str | None = None) -> bool:
        expected = token if token is not None else self.token
        try:
            payload = _http_json(f"http://127.0.0.1:{port}/instance")
        except Exception:
            return False
        from app.desktop_boot import is_our_instance

        return is_our_instance(payload, expected_token=expected)

    def _open_if_running(self) -> bool:
        path = _instance_path()
        if not path.is_file():
            return False
        try:
            inst = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        token = str(inst.get("token") or "")
        api_p = int(inst.get("api_port") or 0)
        web_p = int(inst.get("web_port") or 0)
        if not api_p or not web_p or not token:
            return False
        if self.our_api_running(api_p, token) and _http_ok(f"http://127.0.0.1:{web_p}"):
            self.token = token
            self.api_port = api_p
            self.web_port = web_p
            if os.environ.get("DOCLY_NO_BROWSER") != "1":
                webbrowser.open(f"http://127.0.0.1:{web_p}/app/analyzer")
            return True
        return False

    def run(self) -> str:
        from app.desktop_boot import apply_desktop_env, find_free_port, migrate_sqlite

        self.on_status("files", 10, "Проверка файлов")
        py = _venv_python()
        if not py.is_file():
            raise LaunchError(
                "Не найдена установка Python",
                "Запустите scripts\\windows\\setup-desktop.ps1 один раз, затем повторите.",
            )
        build_id = WEB_DIR / ".next" / "BUILD_ID"
        if not build_id.is_file():
            raise LaunchError(
                "Не собран интерфейс",
                "Нужна установка рабочего стола: scripts\\windows\\setup-desktop.ps1\n"
                "Ярлык не использует dev-сервер и не скачивает PostgreSQL.",
            )
        if not ICON_ICO.is_file():
            raise LaunchError("Нет значка Docly", str(ICON_ICO))
        _check_form_font()

        data_dir = _data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        _runtime_dir().mkdir(parents=True, exist_ok=True)
        self.token = os.environ.get("DOCLY_INSTANCE_TOKEN") or os.urandom(16).hex()
        apply_desktop_env(data_dir=data_dir, instance_token=self.token)
        os.environ["LEGAL_ROOT"] = str(ROOT / "legal")
        os.environ["PYTHONPATH"] = os.pathsep.join([str(API_DIR), str(PY_DAR)])

        if self._open_if_running():
            return "already"

        lock = self.acquire_lock()
        if lock == "busy":
            if self._open_if_running():
                return "already"
            raise LaunchError("Docly уже запускается", "Дождитесь окна или закройте другой запуск.")

        if self._open_if_running():
            self.release_lock()
            return "already"

        self.on_status("storage", 35, "Запуск хранилища")
        try:
            migrate_sqlite(data_dir)
        except Exception as exc:
            self.release_lock()
            raise LaunchError(
                "Не удалось открыть локальную базу",
                "Файл данных повреждён или недоступен для записи.\n"
                f"{data_dir / 'docly.db'}\n{exc}",
            ) from exc

        self.api_port = find_free_port(8000, is_open=_port_open)
        self.web_port = find_free_port(3000, is_open=_port_open)
        os.environ["API_PORT"] = str(self.api_port)
        os.environ["API_HOST"] = "127.0.0.1"
        os.environ["WEB_ORIGIN"] = f"http://127.0.0.1:{self.web_port}"
        os.environ["NEXT_PUBLIC_API_BASE_URL"] = f"http://127.0.0.1:{self.api_port}"
        os.environ["API_PUBLIC_BASE_URL"] = f"http://127.0.0.1:{self.api_port}"

        runtime_js = WEB_DIR / "public" / "docly-runtime.js"
        runtime_js.parent.mkdir(parents=True, exist_ok=True)
        runtime_js.write_text(
            f'window.__DOCLY_API__ = "http://127.0.0.1:{self.api_port}";\n',
            encoding="utf-8",
        )

        self.on_status("service", 60, "Запуск сервиса")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        api_out = (LOG_DIR / "api.out.log").open("ab")
        api_err = (LOG_DIR / "api.err.log").open("ab")
        env = os.environ.copy()
        api_proc = _popen_hidden(
            [
                str(py),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.api_port),
            ],
            cwd=str(API_DIR),
            env=env,
            stdout=api_out,
            stderr=api_err,
        )
        self.children.append(api_proc)

        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.api_port}/live"), 45):
            self._stop_children()
            self.release_lock()
            raise LaunchError("Сервис не запустился", "Смотрите artifacts\\local-run\\api.err.log")
        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.api_port}/ready"), 45):
            self._stop_children()
            self.release_lock()
            raise LaunchError("Хранилище не готово", "Смотрите artifacts\\local-run\\api.err.log")
        if not self.our_api_running(self.api_port):
            self._stop_children()
            self.release_lock()
            raise LaunchError("На порту чужой сервис", f"Порт {self.api_port} занят не Docly.")

        node = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
        next_js = WEB_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
        if not next_js.is_file():
            next_js = ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
        if not Path(node).is_file() or not next_js.is_file():
            self._stop_children()
            self.release_lock()
            raise LaunchError("Не найден Node.js", "Установите Node.js 20+ и выполните setup-desktop.ps1")

        web_out = (LOG_DIR / "web.out.log").open("ab")
        web_err = (LOG_DIR / "web.err.log").open("ab")
        web_env = env.copy()
        web_env["PORT"] = str(self.web_port)
        web_env["HOSTNAME"] = "127.0.0.1"
        web_proc = _popen_hidden(
            [str(node), str(next_js), "start", "--port", str(self.web_port), "--hostname", "127.0.0.1"],
            cwd=str(WEB_DIR),
            env=web_env,
            stdout=web_out,
            stderr=web_err,
        )
        self.children.append(web_proc)
        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.web_port}"), 90):
            self._stop_children()
            self.release_lock()
            raise LaunchError("Интерфейс не открылся", "Смотрите artifacts\\local-run\\web.err.log")

        _instance_path().write_text(
            json.dumps(
                {
                    "token": self.token,
                    "api_port": self.api_port,
                    "web_port": self.web_port,
                    "api_pid": api_proc.pid,
                    "web_pid": web_proc.pid,
                    "data_dir": str(data_dir),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.on_status("open", 100, "Открытие приложения")
        if os.environ.get("DOCLY_NO_BROWSER") != "1":
            webbrowser.open(f"http://127.0.0.1:{self.web_port}/app/analyzer")
        self.release_lock()
        return "started"

    def _wait(self, pred, seconds: int) -> bool:
        deadline = time.time() + seconds
        while time.time() < deadline:
            if pred():
                return True
            time.sleep(0.4)
        return False

    def _stop_children(self) -> None:
        for proc in self.children:
            if proc.poll() is None:
                proc.terminate()
        time.sleep(0.6)
        for proc in self.children:
            if proc.poll() is None:
                proc.kill()
        self.children.clear()


def stop_instance() -> int:
    path = _instance_path()
    if not path.is_file():
        print("not_running")
        return 0
    try:
        inst = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("not_running")
        return 0
    token = str(inst.get("token") or "")
    api_port = int(inst.get("api_port") or 0)
    pids = [int(inst.get("api_pid") or 0), int(inst.get("web_pid") or 0)]
    if api_port:
        try:
            payload = _http_json(f"http://127.0.0.1:{api_port}/instance")
        except Exception:
            payload = {}
        if payload:
            from app.desktop_boot import is_our_instance

            if not is_our_instance(payload, expected_token=token):
                print("foreign_instance")
                return 2
            extra = int(payload.get("pid") or 0)
            if extra and extra not in pids:
                pids.append(extra)
    for pid in pids:
        _terminate_pid(pid, force=True)
    deadline = time.time() + 5
    while time.time() < deadline:
        if not any(_pid_alive(pid) for pid in pids if pid):
            break
        time.sleep(0.2)
        for pid in pids:
            _terminate_pid(pid, force=True)
    try:
        path.unlink()
    except OSError:
        pass
    print("stopped")
    return 0


def _terminate_pid(pid: int, *, force: bool = False) -> None:
    if pid <= 0:
        return
    if sys.platform == "win32":
        args = ["taskkill", "/PID", str(pid), "/T"]
        if force:
            args.append("/F")
        subprocess.run(args, capture_output=True, creationflags=CREATE_NO_WINDOW, check=False)
        return
    if not _pid_alive(pid):
        return
    try:
        os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
    except OSError:
        pass


def run_headless() -> int:
    launcher = DoclyLauncher()
    try:
        result = launcher.run()
        print(result)
        return 0
    except LaunchError as exc:
        print(exc.title, file=sys.stderr)
        print(exc.details, file=sys.stderr)
        return 1


def run_splash() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText
    except Exception:
        return run_headless()

    root = tk.Tk()
    root.title("Docly")
    root.geometry("520x420")
    root.resizable(False, False)

    launcher = DoclyLauncher()
    status_var = tk.StringVar(value="Запуск Docly…")
    detail_visible = tk.BooleanVar(value=False)

    if LOGO_PNG.is_file():
        try:
            img = tk.PhotoImage(file=str(LOGO_PNG))
            tk.Label(root, image=img).pack(pady=(16, 4))
            root._logo = img  # type: ignore[attr-defined]
        except Exception:
            tk.Label(root, text="Docly", font=("Segoe UI", 18, "bold")).pack(pady=12)
    else:
        tk.Label(root, text="Docly", font=("Segoe UI", 18, "bold")).pack(pady=12)

    tk.Label(root, textvariable=status_var, font=("Segoe UI", 12)).pack()
    bar = ttk.Progressbar(root, length=440, mode="determinate")
    bar.pack(pady=10)

    details = ScrolledText(root, height=8, state="disabled")
    btn_row = tk.Frame(root)
    btn_row.pack(pady=8)

    def append_details(text: str) -> None:
        details.configure(state="normal")
        details.insert("end", text + "\n")
        details.configure(state="disabled")

    def set_status(stage: str, pct: int, msg: str) -> None:
        status_var.set(msg)
        bar["value"] = pct
        append_details(msg)
        launcher.log(msg)

    launcher.on_status = lambda s, p, m: root.after(0, lambda: set_status(s, p, m))

    def copy_diag() -> None:
        root.clipboard_clear()
        root.clipboard_append(launcher.diagnostics())

    def toggle_details() -> None:
        if detail_visible.get():
            details.pack_forget()
            detail_visible.set(False)
        else:
            details.pack(fill="both", padx=16, pady=4)
            detail_visible.set(True)

    def do_run() -> None:
        def worker() -> None:
            try:
                result = launcher.run()
                if result in {"started", "already"}:
                    root.after(0, root.destroy)
                else:
                    root.after(0, lambda: status_var.set("Готово"))
            except LaunchError as exc:
                def fail() -> None:
                    status_var.set(exc.title)
                    append_details(exc.details)
                    retry_btn.configure(state="normal")

                root.after(0, fail)
            except Exception:
                tb = traceback.format_exc()
                launcher.log(tb)

                def fail2() -> None:
                    status_var.set("Непредвиденная ошибка")
                    append_details(tb)
                    retry_btn.configure(state="normal")

                root.after(0, fail2)

        retry_btn.configure(state="disabled")
        threading.Thread(target=worker, daemon=True).start()

    tk.Button(btn_row, text="Показать подробности", command=toggle_details).pack(side="left", padx=4)
    retry_btn = tk.Button(btn_row, text="Повторить", command=do_run, state="disabled")
    retry_btn.pack(side="left", padx=4)
    tk.Button(btn_row, text="Скопировать диагностику", command=copy_diag).pack(side="left", padx=4)

    root.protocol("WM_DELETE_WINDOW", root.destroy)
    root.after(200, do_run)
    root.mainloop()
    return 0


if __name__ == "__main__":
    if "--stop" in sys.argv:
        raise SystemExit(stop_instance())
    if "--headless" in sys.argv or os.environ.get("DOCLY_HEADLESS") == "1":
        raise SystemExit(run_headless())
    raise SystemExit(run_splash())
