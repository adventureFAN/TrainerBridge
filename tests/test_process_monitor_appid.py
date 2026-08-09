import sys
import types
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# core.steam imports vdf at module import time. The production virtual environment
# provides it; this tiny fallback keeps this focused regression test runnable in
# minimal static-review environments too.
try:
    import vdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["vdf"] = types.ModuleType("vdf")

from core.process_monitor import ProcessMonitor


class ProcessMonitorAppIdTests(unittest.TestCase):
    def setUp(self):
        self.monitor = ProcessMonitor(steam_kind="native")

    @staticmethod
    def process(*args):
        args = list(args)
        return {
            "pid": 12345,
            "ppid": 1,
            "args": args,
            "cmdline": " ".join(args),
            "executable": "/usr/bin/env",
        }

    def test_exact_appid_argument_is_accepted(self):
        process = self.process(
            "/usr/bin/reaper",
            "SteamLaunch",
            "AppId=123",
            "waitforexitandrun",
            "game.exe",
        )
        self.assertTrue(self.monitor._is_real_launch_process(process, "123"))

    def test_longer_appid_is_not_a_match(self):
        process = self.process(
            "/usr/bin/reaper",
            "SteamLaunch",
            "AppId=1234",
            "waitforexitandrun",
            "game.exe",
        )
        self.assertFalse(self.monitor._is_real_launch_process(process, "123"))

    def test_appid_text_inside_another_argument_is_not_a_match(self):
        process = self.process(
            "/usr/bin/reaper",
            "SteamLaunch",
            "prefix-AppId=123-suffix",
            "waitforexitandrun",
            "game.exe",
        )
        self.assertFalse(self.monitor._is_real_launch_process(process, "123"))

    def test_install_launch_is_still_rejected(self):
        process = self.process(
            "/usr/bin/reaper",
            "SteamLaunch",
            "AppId=123",
            "Install=1",
            "game.exe",
        )
        self.assertFalse(self.monitor._is_real_launch_process(process, "123"))

    def test_iscriptevaluator_is_still_rejected(self):
        process = self.process(
            "/usr/bin/reaper",
            "SteamLaunch",
            "AppId=123",
            "iscriptevaluator.exe",
        )
        self.assertFalse(self.monitor._is_real_launch_process(process, "123"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
