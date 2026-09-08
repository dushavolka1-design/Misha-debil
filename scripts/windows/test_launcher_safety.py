"""Dependency-free launcher regressions; Windows kernel tests run separately."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import queue
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location("docly_launcher", Path(__file__).with_name("docly_launcher.py"))
assert SPEC and SPEC.loader
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class LauncherSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        env = patch.dict(os.environ, {"DOCLY_RUNTIME_DIR": self.temp.name})
        env.start()
        self.addCleanup(env.stop)
        self.path = Path(self.temp.name) / "instance.json"
        self.record = {
            "api_pid": 101,
            "web_pid": 102,
            "install_root": str(launcher.ROOT),
            "process_identities": {
                "101": {"created": 1001, "exe": "python.exe"},
                "102": {"created": 1002, "exe": "node.exe"},
            },
        }

    def save(self):
        self.path.write_text(json.dumps(self.record), encoding="utf-8")

    def stop(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return launcher.stop_instance()

    def test_missing_manifest_is_not_running(self):
        self.assertEqual(self.stop(), 0)

    def test_legacy_pid_file_never_kills_a_process(self):
        self.path.write_text('{"api_pid":101,"web_pid":102,"api_port":8000}', encoding="utf-8")
        with patch.object(launcher, "_windows_process") as terminate:
            self.assertEqual(self.stop(), 2)
            terminate.assert_not_called()
        self.assertTrue(self.path.exists())

    def test_malformed_manifest_retained(self):
        for value in ('{', 'null', '[]', '{"api_pid":"bad"}'):
            with self.subTest(value=value):
                self.path.write_text(value, encoding="utf-8")
                self.assertEqual(self.stop(), 2)
                self.assertTrue(self.path.exists())

    def test_foreign_installation_is_not_stopped(self):
        self.record["install_root"] = "another installation"
        self.save()
        with patch.object(launcher, "_windows_process") as terminate:
            self.assertEqual(self.stop(), 2)
            terminate.assert_not_called()

    def test_reused_pid_is_not_stopped(self):
        self.save()
        with patch.object(launcher, "_pid_alive", return_value=True), patch.object(
            launcher, "_windows_process", return_value={"created": 9999, "exe": "python.exe"}
        ) as process:
            self.assertEqual(self.stop(), 2)
            self.assertEqual(process.call_count, 1)
            self.assertEqual(process.call_args.kwargs, {})
        self.assertTrue(self.path.exists())

    def test_all_processes_verified_before_first_termination(self):
        self.save()
        with patch.object(launcher, "_pid_alive", return_value=True), patch.object(
            launcher, "_windows_process", side_effect=[self.record["process_identities"]["101"], OSError("denied")]
        ) as process:
            self.assertEqual(self.stop(), 2)
            self.assertTrue(all(not call.kwargs for call in process.call_args_list))
        self.assertTrue(self.path.exists())

    def test_unreachable_api_does_not_prevent_verified_stop(self):
        self.save()
        def process(pid, expected=None):
            return self.record["process_identities"][str(pid)]
        with patch.object(launcher, "_http_json", side_effect=OSError("offline")) as http, patch.object(
            launcher, "_pid_alive", return_value=True
        ), patch.object(launcher, "_windows_process", side_effect=process) as kernel:
            self.assertEqual(self.stop(), 0)
            self.assertEqual(kernel.call_count, 4)
            self.assertEqual(sum("expected" in c.kwargs for c in kernel.call_args_list), 2)
            http.assert_not_called()
        self.assertFalse(self.path.exists())
        self.assertEqual(self.stop(), 0)

    def test_termination_failure_is_not_reported_as_success(self):
        self.save()
        identities = self.record["process_identities"]
        with patch.object(launcher, "_pid_alive", return_value=True), patch.object(
            launcher, "_windows_process", side_effect=[identities["101"], identities["102"], OSError("timeout")]
        ):
            self.assertEqual(self.stop(), 2)
        self.assertTrue(self.path.exists())

    def test_failed_launch_reaps_real_child_and_releases_lock(self):
        obj = launcher.DoclyLauncher()
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        def fail():
            self.assertIsNone(obj.acquire_lock())
            obj.children.append(proc)
            raise RuntimeError("synthetic failure after spawn")
        with patch.object(obj, "_run", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                obj.run()
        self.assertIsNotNone(proc.poll())
        self.assertEqual(obj.children, [])
        self.assertIsNone(obj._lock_fh)
        guard = launcher.DoclyLauncher()
        self.assertIsNone(guard.acquire_lock())
        guard.release_lock()

    def test_cancelled_launch_does_not_start(self):
        obj = launcher.DoclyLauncher()
        obj.cancelled.set()
        with patch.object(obj, "_run") as run:
            with self.assertRaises(launcher.LaunchError):
                obj.run()
            run.assert_not_called()

    def test_cancel_interrupts_readiness_wait(self):
        obj = launcher.DoclyLauncher()
        obj.cancelled.set()
        with self.assertRaises(launcher.LaunchError):
            obj._wait(lambda: False, 90)

    def test_splash_error_survives_except_scope(self):
        obj = Mock()
        obj.run.side_effect = launcher.LaunchError("Ошибка", "Подробности")
        events = queue.Queue()
        launcher._splash_worker(obj, events)
        self.assertEqual(events.get_nowait(), ("error", "Ошибка", "Подробности"))

    def test_splash_unexpected_error_is_transferred_without_tk(self):
        obj = Mock()
        obj.run.side_effect = RuntimeError("synthetic")
        events = queue.Queue()
        launcher._splash_worker(obj, events)
        event = events.get_nowait()
        self.assertEqual(event[:2], ("error", "Непредвиденная ошибка"))
        self.assertIn("RuntimeError: synthetic", event[2])

    def test_headless_unexpected_error_returns_nonzero(self):
        with patch.object(launcher.DoclyLauncher, "_run", side_effect=RuntimeError("synthetic")):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(launcher.run_headless(), 1)


if __name__ == "__main__":
    unittest.main()
