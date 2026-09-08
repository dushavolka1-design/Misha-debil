"""Real Windows kernel acceptance for process identity (not installer acceptance)."""
from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("docly_launcher", Path(__file__).with_name("docly_launcher.py"))
assert SPEC and SPEC.loader
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


class WindowsProcessTests(unittest.TestCase):
    def setUp(self):
        if sys.platform != "win32":
            self.fail("This acceptance suite must run on Windows; do not count a skip as success")
        self.proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=10)

    def test_creation_time_mismatch_keeps_real_process_alive(self):
        identity = launcher._windows_process(self.proc.pid)
        with self.assertRaises(OSError):
            launcher._windows_process(self.proc.pid, expected={**identity, "created": identity["created"] + 1})
        self.assertIsNone(self.proc.poll())

    def test_executable_mismatch_keeps_real_process_alive(self):
        identity = launcher._windows_process(self.proc.pid)
        with self.assertRaises(OSError):
            launcher._windows_process(self.proc.pid, expected={**identity, "exe": "foreign.exe"})
        self.assertIsNone(self.proc.poll())

    def test_matching_handle_terminates_and_waits(self):
        identity = launcher._windows_process(self.proc.pid)
        self.assertGreater(identity["created"], 0)
        self.assertTrue(Path(identity["exe"]).is_file())
        self.assertTrue(launcher._pid_alive(self.proc.pid))
        launcher._windows_process(self.proc.pid, expected=identity)
        self.proc.wait(timeout=1)
        self.assertIsNotNone(self.proc.returncode)
        self.assertFalse(launcher._pid_alive(self.proc.pid))


if __name__ == "__main__":
    unittest.main()
