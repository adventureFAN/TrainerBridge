import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import vdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["vdf"] = types.ModuleType("vdf")

from core.exporter import _STANDARD_GAME_DETECTOR, _build_standard_script


class StandardExporterGameDetectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.proc = self.root / "proc"
        self.proc.mkdir()
        self.detector = self.root / "detector.py"
        self.detector.write_text(_STANDARD_GAME_DETECTOR, encoding="utf-8")

    def tearDown(self):
        self.tempdir.cleanup()

    def write_process(self, pid, ppid, args, executable="/usr/bin/env"):
        proc_dir = self.proc / str(pid)
        proc_dir.mkdir()
        proc_dir.joinpath("cmdline").write_bytes(
            b"\0".join(str(arg).encode("utf-8") for arg in args) + b"\0"
        )
        proc_dir.joinpath("status").write_text(
            f"Name:\ttest\nPPid:\t{ppid}\n",
            encoding="utf-8",
        )
        os.symlink(executable, proc_dir / "exe")

    def run_detector(self, appid="123", mode="once", timeout="1", stable="0", interval="0.01"):
        return subprocess.run(
            [
                sys.executable,
                str(self.detector),
                str(appid),
                mode,
                str(timeout),
                str(stable),
                str(interval),
                str(self.proc),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def write_launch(self, appid="123", pid=100):
        self.write_process(
            pid,
            1,
            [
                "/usr/bin/reaper",
                "SteamLaunch",
                f"AppId={appid}",
                "waitforexitandrun",
                r"Z:\\Games\\Test Game.exe",
            ],
        )

    def test_launch_process_alone_is_not_enough(self):
        self.write_launch()
        result = self.run_detector()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_actual_game_wine_process_is_required(self):
        self.write_launch()
        self.write_process(
            101,
            100,
            [r"Z:\\Games\\Test Game.exe"],
            executable="/usr/bin/wine64-preloader",
        )
        result = self.run_detector()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "101\tTest Game.exe")

    def test_helper_wine_process_with_steam_exe_first_is_rejected(self):
        self.write_launch()
        self.write_process(
            101,
            100,
            ["steam.exe", r"Z:\\Games\\Test Game.exe"],
            executable="/usr/bin/wine-preloader",
        )
        result = self.run_detector()
        self.assertEqual(result.returncode, 2)

    def test_exact_appid_is_still_required(self):
        self.write_launch(appid="1234")
        self.write_process(
            101,
            100,
            [r"Z:\\Games\\Test Game.exe"],
            executable="/usr/bin/wine64-preloader",
        )
        result = self.run_detector(appid="123")
        self.assertEqual(result.returncode, 2)

    def test_wait_mode_requires_stable_game_pid(self):
        self.write_launch()
        self.write_process(
            101,
            100,
            [r"Z:\\Games\\Test Game.exe"],
            executable="/usr/bin/wine64-preloader",
        )
        result = self.run_detector(
            mode="wait",
            timeout="0.5",
            stable="0.05",
            interval="0.01",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "101\tTest Game.exe")

    def test_generated_standard_script_uses_actual_game_detector_and_is_valid_bash(self):
        game = SimpleNamespace(
            appid="123",
            name="Test Game",
            prefix=self.root / "compatdata" / "123",
            trainer_path=self.root / "trainer.exe",
        )
        proton = self.root / "proton"
        steam_info = {
            "install_path": str(self.root / "steam"),
            "launch_prefix": ("/usr/bin/steam",),
        }
        script = _build_standard_script(game, steam_info, proton)
        self.assertIn("Waiting for the actual game executable to remain stable...", script)
        self.assertIn("Game detected: $GAME_EXECUTABLE (PID $GAME_PID).", script)
        self.assertIn("wine64-preloader", script)
        self.assertNotIn("session_detected()", script)

        script_path = self.root / "launch.sh"
        script_path.write_text(script, encoding="utf-8")
        result = subprocess.run(
            ["bash", "-n", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
