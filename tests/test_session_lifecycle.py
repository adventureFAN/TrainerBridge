from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


try:
    import vdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["vdf"] = types.ModuleType("vdf")

from core.trainer_launcher import TrainerLauncher
from core.trainer_process import (
    request_trainer_process_stop,
    stop_trainer_process,
    trainer_process_is_running,
)


class TrainerProcessGroupTests(unittest.TestCase):
    def test_launcher_starts_trainer_in_own_session(self):
        launcher = TrainerLauncher(Path("/tmp/steam"))
        game = SimpleNamespace(
            prefix=Path("/tmp/prefix"),
            trainer_path=Path("/tmp/trainer.exe"),
        )

        with mock.patch.object(
            launcher,
            "build_command",
            return_value=["/tmp/proton", "runinprefix", "/tmp/trainer.exe"],
        ), mock.patch.object(
            launcher,
            "build_environment",
            return_value={},
        ), mock.patch(
            "core.trainer_launcher.subprocess.Popen"
        ) as popen:
            launcher.launch(game)

        self.assertTrue(popen.call_args.kwargs["start_new_session"])

    def test_running_wrapper_counts_as_running(self):
        process = mock.Mock()
        process.poll.return_value = None

        self.assertTrue(trainer_process_is_running(process, 12345))

    def test_exited_wrapper_still_counts_as_running_while_group_exists(self):
        process = mock.Mock()
        process.poll.return_value = 0

        with mock.patch(
            "core.trainer_process.os.killpg",
            return_value=None,
        ) as killpg:
            self.assertTrue(trainer_process_is_running(process, 12345))

        killpg.assert_called_once_with(12345, 0)

    def test_stop_request_targets_whole_process_group(self):
        process = mock.Mock()
        process.poll.return_value = None

        with mock.patch(
            "core.trainer_process.os.killpg",
            return_value=None,
        ) as killpg:
            self.assertTrue(
                request_trainer_process_stop(
                    process,
                    process_group=12345,
                )
            )

        killpg.assert_called_once_with(12345, signal.SIGTERM)
        process.terminate.assert_not_called()

    def test_force_stop_targets_whole_process_group(self):
        process = mock.Mock()
        process.poll.return_value = None

        with mock.patch(
            "core.trainer_process.os.killpg",
            return_value=None,
        ) as killpg:
            self.assertTrue(
                request_trainer_process_stop(
                    process,
                    process_group=12345,
                    force=True,
                )
            )

        killpg.assert_called_once_with(12345, signal.SIGKILL)
        process.kill.assert_not_called()

    def test_real_process_group_is_stopped(self):
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                (
                    "import subprocess, sys, time; "
                    "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
                    "time.sleep(30)"
                ),
            ],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            time.sleep(0.15)
            self.assertTrue(
                trainer_process_is_running(process, process.pid)
            )
            self.assertTrue(
                stop_trainer_process(
                    process,
                    process_group=process.pid,
                    timeout=1.0,
                )
            )
        finally:
            if trainer_process_is_running(process, process.pid):
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

        self.assertFalse(
            trainer_process_is_running(process, process.pid)
        )


class MainWindowLifecycleWiringTests(unittest.TestCase):
    def setUp(self):
        self.main_source = (PROJECT_ROOT / "main.py").read_text(
            encoding="utf-8"
        )
        self.session_source = (
            PROJECT_ROOT / "core" / "session_manager.py"
        ).read_text(encoding="utf-8")

    def test_sessions_record_trainer_process_group(self):
        self.assertIn(
            '"trainer_process_group": trainer_process.pid',
            self.session_source,
        )
        self.assertIn(
            '"trainer_process_group": trainer_session["trainer_process_group"]',
            self.session_source,
        )

    def test_game_exit_requests_trainer_shutdown(self):
        self.assertIn(
            '"trainer_stop_reason"\n                    ] = "game_exit"',
            self.main_source,
        )
        self.assertIn(
            "Game exited; stopping the TrainerBridge-launched trainer...",
            self.main_source,
        )
        self.assertIn(
            "request_trainer_process_stop(",
            self.main_source,
        )

    def test_intentional_game_exit_stop_does_not_trigger_early_exit_hint(self):
        self.assertIn(
            'stop_reason != "game_exit"',
            self.main_source,
        )
        self.assertIn(
            "because the game exited.",
            self.main_source,
        )

    def test_stubborn_trainer_has_forced_shutdown_fallback(self):
        self.assertIn(
            "TRAINER_AUTO_STOP_GRACE_SECONDS = 3",
            self.main_source,
        )
        self.assertIn(
            '"trainer_force_stop_requested"',
            self.main_source,
        )
        self.assertIn(
            "force=True",
            self.main_source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
