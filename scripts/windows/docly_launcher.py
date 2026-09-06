# -*- coding: utf-8 -*-
"""Visible Docly desktop launcher. No Docker, no PostgreSQL/Redis download."""
from __future__ import annotations

import json
import os
import queue
import shutil
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
        from ctypes import WinDLL, wintypes

        kernel = WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if not handle:
            # Access denied is not proof that a process has stopped.
            import ctypes

            return ctypes.get_last_error() != 87
        try:
            return kernel.WaitForSingleObject(handle, 0) != 0
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
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
        self.cancelled = threading.Event()

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
            if not isinstance(inst, dict):
                return False
            token = str(inst.get("token") or "")
            api_p = int(inst.get("api_port") or 0)
            web_p = int(inst.get("web_port") or 0)
        except (OSError, ValueError, TypeError):
            return False
        if not 0 < api_p < 65536 or not 0 < web_p < 65536 or not token:
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
        """Always release locks and reap owned children after a failed launch."""
        try:
            self._check_cancelled()
            result = self._run()
            self._check_cancelled()
            return result
        except BaseException:
            self._stop_children()
            raise
        finally:
            self.release_lock()

    def _check_cancelled(self) -> None:
        if self.cancelled.is_set():
            raise LaunchError("Запуск отменён", "Процессы незавершённого запуска остановлены.")

    def _run(self) -> str:
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
            return "already"

        self.on_status("storage", 35, "Запуск хранилища")
        try:
            migrate_sqlite(data_dir)
        except Exception as exc:
            raise LaunchError(
                "Не удалось открыть локальную базу",
                "Файл данных повреждён или недоступен для записи.\n"
                f"{data_dir / 'docly.db'}\n{exc}",
            ) from exc

        self._check_cancelled()
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
        env = os.environ.copy()
        with (LOG_DIR / "api.out.log").open("ab") as api_out, (LOG_DIR / "api.err.log").open("ab") as api_err:
            api_proc = _popen_hidden(
                [str(py), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self.api_port)],
                cwd=str(API_DIR), env=env, stdout=api_out, stderr=api_err,
            )
        self.children.append(api_proc)

        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.api_port}/live"), 45):
            raise LaunchError("Сервис не запустился", "Смотрите artifacts\\local-run\\api.err.log")
        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.api_port}/ready"), 45):
            raise LaunchError("Хранилище не готово", "Смотрите artifacts\\local-run\\api.err.log")
        if not self.our_api_running(self.api_port):
            raise LaunchError("На порту чужой сервис", f"Порт {self.api_port} занят не Docly.")

        bundled_node = ROOT / "runtime" / "node" / "node.exe"
        node = str(bundled_node) if bundled_node.is_file() else shutil.which("node")
        next_js = WEB_DIR / "node_modules" / "next" / "dist" / "bin" / "next"
        if not next_js.is_file():
            next_js = ROOT / "node_modules" / "next" / "dist" / "bin" / "next"
        if not node or not Path(node).is_file() or not next_js.is_file():
            raise LaunchError("Не найден Node.js", "Повторите установку Docly: отсутствует runtime или интерфейс.")

        web_env = env.copy()
        web_env["PORT"] = str(self.web_port)
        web_env["HOSTNAME"] = "127.0.0.1"
        self._check_cancelled()
        with (LOG_DIR / "web.out.log").open("ab") as web_out, (LOG_DIR / "web.err.log").open("ab") as web_err:
            web_proc = _popen_hidden(
                [str(node), str(next_js), "start", "--port", str(self.web_port), "--hostname", "127.0.0.1"],
                cwd=str(WEB_DIR), env=web_env, stdout=web_out, stderr=web_err,
            )
        self.children.append(web_proc)
        if not self._wait(lambda: _http_ok(f"http://127.0.0.1:{self.web_port}"), 90):
            raise LaunchError("Интерфейс не открылся", "Смотрите artifacts\\local-run\\web.err.log")

        identities = {}
        if sys.platform == "win32":
            for proc in self.children:
                if proc.poll() is not None:
                    raise LaunchError("Процесс Docly завершился", "Запуск не завершён; повторите попытку.")
                identities[str(proc.pid)] = _windows_process(proc.pid)
                if proc.poll() is not None:
                    raise LaunchError("Процесс Docly завершился", "Не удалось подтвердить владение процессом.")
        instance = {
            "token": self.token,
            "api_port": self.api_port,
            "web_port": self.web_port,
            "api_pid": api_proc.pid,
            "web_pid": web_proc.pid,
            "data_dir": str(data_dir),
            "install_root": str(ROOT),
            "process_identities": identities,
        }
        temporary = _instance_path().with_suffix(".tmp")
        temporary.write_text(json.dumps(instance, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(_instance_path())
        self.on_status("open", 100, "Открытие приложения")
        if os.environ.get("DOCLY_NO_BROWSER") != "1":
            webbrowser.open(f"http://127.0.0.1:{self.web_port}/app/analyzer")
        return "started"

    def _wait(self, pred, seconds: int) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check_cancelled()
            if pred():
                return True
            self.cancelled.wait(0.4)
        return False

    def _stop_children(self) -> None:
        failures = []
        for proc in self.children:
            try:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            except OSError:
                if proc.poll() is None:
                    failures.append(proc)
            except subprocess.TimeoutExpired:
                failures.append(proc)
        self.children = failures
        if failures:
            raise LaunchError("Не удалось остановить Docly", "Не все дочерние процессы завершились; повторите остановку.")


def _windows_process(pid: int, expected: dict | None = None) -> dict:
    """Query and optionally terminate through the SAME handle, never a reused PID.

    Metadata protects against stale PID reuse, not a malicious same-user writer.
    No process-tree kill: descendants have not been independently authenticated.
    """
    import ctypes
    from ctypes import wintypes

    if sys.platform != "win32" or isinstance(pid, bool) or not 0 < pid <= 0xFFFFFFFF:
        raise OSError("Unsupported process identity")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateProcess.restype = wintypes.BOOL
    access = 0x1000 | 0x00100000 | (0x0001 if expected is not None else 0)
    handle = kernel.OpenProcess(access, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        creation, exit_time, system, user = (wintypes.FILETIME() for _ in range(4))
        if not kernel.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(system), ctypes.byref(user)):
            raise ctypes.WinError(ctypes.get_last_error())
        size = wintypes.DWORD(32768)
        image = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        actual = {
            "created": (creation.dwHighDateTime << 32) | creation.dwLowDateTime,
            "exe": os.path.normcase(os.path.realpath(image.value)),
        }
        if expected is not None:
            if actual != expected:
                raise OSError("Process identity mismatch; refusing termination")
            if kernel.WaitForSingleObject(handle, 0) != 0:
                if not kernel.TerminateProcess(handle, 1):
                    raise ctypes.WinError(ctypes.get_last_error())
                if kernel.WaitForSingleObject(handle, 5000) != 0:
                    raise OSError("Process did not stop within five seconds")
        return actual
    finally:
        kernel.CloseHandle(handle)


def stop_instance() -> int:
    guard = DoclyLauncher()
    if guard.acquire_lock() == "busy":
        print("launcher_busy")
        return 2
    try:
        return _stop_instance_locked()
    finally:
        guard.release_lock()


def _stop_instance_locked() -> int:
    path = _instance_path()
    if not path.is_file():
        print("not_running")
        return 0
    try:
        inst = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(inst, dict):
            raise ValueError("Invalid instance record")
        pids = [inst["api_pid"], inst["web_pid"]]
        if any(type(pid) is not int or not 0 < pid <= 0xFFFFFFFF for pid in pids):
            raise ValueError("Invalid process ID")
        identities = inst.get("process_identities")
        if inst.get("install_root") != str(ROOT) or not isinstance(identities, dict):
            raise ValueError("Legacy or foreign instance record")
        for pid in pids:
            identity = identities.get(str(pid))
            if not isinstance(identity, dict) or set(identity) != {"created", "exe"}:
                raise ValueError("Missing process identity")
            if type(identity["created"]) is not int or identity["created"] <= 0 or not isinstance(identity["exe"], str):
                raise ValueError("Invalid process identity")
    except (OSError, ValueError, KeyError, TypeError):
        print("unverified_instance: stop refused; instance record retained")
        return 2
    try:
        # Validate every live process BEFORE stopping any; recheck on the handle
        # used for termination to close the PID-reuse race.
        live = [pid for pid in pids if _pid_alive(pid)]
        for pid in live:
            if _windows_process(pid) != identities[str(pid)]:
                raise OSError("Process identity mismatch")
        for pid in live:
            _windows_process(pid, expected=identities[str(pid)])
        path.unlink()
    except OSError:
        print("stop_failed: ownership or termination unconfirmed; instance record retained")
        return 2
    print("stopped")
    return 0


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
    except Exception:
        print("Непредвиденная ошибка запуска Docly", file=sys.stderr)
        return 1


def _splash_worker(launcher: DoclyLauncher, events: queue.Queue) -> None:
    """Transfer immutable error text; never call Tk from the worker thread."""
    try:
        events.put(("done", launcher.run()))
    except LaunchError as exc:
        events.put(("error", exc.title, exc.details))
    except Exception:
        events.put(("error", "Непредвиденная ошибка", traceback.format_exc()))


def run_splash() -> int:
    try:
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText

        root = tk.Tk()
    except Exception:
        return run_headless()

    root.title("Docly")
    root.geometry("520x420")
    root.resizable(False, False)
    launcher = DoclyLauncher()
    events = queue.Queue()
    worker = None
    closing = False
    outcome = 1
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

    launcher.on_status = lambda s, p, m: events.put(("status", s, p, m))

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
        nonlocal worker
        if closing or (worker is not None and worker.is_alive()):
            return
        retry_btn.configure(state="disabled")
        worker = threading.Thread(target=_splash_worker, args=(launcher, events), daemon=False)
        worker.start()

    def close() -> None:
        nonlocal closing
        closing = True
        launcher.cancelled.set()
        retry_btn.configure(state="disabled")
        status_var.set("Остановка запуска…")

    def poll() -> None:
        nonlocal outcome
        if closing:
            if worker is None or not worker.is_alive():
                root.destroy()
                return
        else:
            while not events.empty():
                event = events.get_nowait()
                if event[0] == "status":
                    status_var.set(event[3])
                    bar["value"] = event[2]
                    append_details(event[3])
                    launcher.log(event[3])
                elif event[0] == "error":
                    status_var.set(event[1])
                    append_details(event[2])
                    retry_btn.configure(state="normal")
                elif event[0] == "done":
                    outcome = 0
                    root.destroy()
                    return
        root.after(50, poll)

    def callback_error(_kind, _value, _tb) -> None:
        # Tk otherwise prints and suppresses callback errors, leaving workers alive.
        nonlocal closing
        closing = True
        launcher.cancelled.set()
        root.after(50, poll)

    root.report_callback_exception = callback_error
    tk.Button(btn_row, text="Показать подробности", command=toggle_details).pack(side="left", padx=4)
    retry_btn = tk.Button(btn_row, text="Повторить", command=do_run, state="disabled")
    retry_btn.pack(side="left", padx=4)
    tk.Button(btn_row, text="Скопировать диагностику", command=copy_diag).pack(side="left", padx=4)
    root.protocol("WM_DELETE_WINDOW", close)
    root.after(200, do_run)
    root.after(50, poll)
    try:
        root.mainloop()
    finally:
        if outcome != 0:
            launcher.cancelled.set()
            if worker is not None:
                worker.join()
            launcher._stop_children()
            launcher.release_lock()
    return outcome


if __name__ == "__main__":
    if "--stop" in sys.argv:
        raise SystemExit(stop_instance())
    if "--headless" in sys.argv or os.environ.get("DOCLY_HEADLESS") == "1":
        raise SystemExit(run_headless())
    raise SystemExit(run_splash())
