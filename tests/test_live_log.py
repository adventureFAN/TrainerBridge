import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class LiveLogTests(unittest.TestCase):

    def test_formatter_uses_timestamp_and_known_level(self):
        from core.live_log import format_live_log_entry

        result = format_live_log_entry(
            "Trainer started.",
            "OK",
            datetime(2026, 8, 8, 23, 42, 7)
        )

        self.assertEqual(
            result,
            "23:42:07  OK       Trainer started."
        )


    def test_formatter_normalizes_unknown_level_to_info(self):
        from core.live_log import format_live_log_entry

        result = format_live_log_entry(
            "Example",
            "debug",
            datetime(2026, 8, 8, 1, 2, 3)
        )

        self.assertIn(
            "01:02:03  INFO     Example",
            result
        )


    def test_formatter_shortens_bazzite_home_paths(self):
        from core.live_log import format_live_log_entry

        result = format_live_log_entry(
            (
                "Steam: /home/testuser/.steam/steam; "
                "Proton: /var/home/testuser/.local/share/Steam/tool"
            ),
            "INFO",
            datetime(2026, 8, 9, 0, 5, 6),
            home="/var/home/testuser"
        )

        self.assertEqual(
            result,
            (
                "00:05:06  INFO     "
                "Steam: ~/.steam/steam; "
                "Proton: ~/.local/share/Steam/tool"
            )
        )


    def test_home_shortening_does_not_touch_similar_username(self):
        from core.live_log import sanitize_live_log_message

        result = sanitize_live_log_message(
            "Other user: /home/otheruser/example",
            home="/home/testuser"
        )

        self.assertEqual(
            result,
            "Other user: /home/otheruser/example"
        )


    def test_home_directory_itself_is_shortened(self):
        from core.live_log import sanitize_live_log_message

        self.assertEqual(
            sanitize_live_log_message(
                "/var/home/testuser",
                home="/var/home/testuser"
            ),
            "~"
        )


    def test_logging_setup_has_no_file_handler_or_stream_redirect(self):
        source = (
            PROJECT_ROOT / "core" / "logging_setup.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("FileHandler", source)
        self.assertNotIn("LOG_DIR", source)
        self.assertNotIn("sys.stdout", source)
        self.assertNotIn("sys.stderr", source)


    def test_normal_logging_setup_creates_no_log_file(self):
        with tempfile.TemporaryDirectory() as temp_home:
            env = os.environ.copy()
            env["HOME"] = temp_home
            env["PYTHONPATH"] = str(PROJECT_ROOT)

            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "from core.logging_setup import setup_logging; "
                        "setup_logging(); print('done')"
                    )
                ],
                check=True,
                cwd=PROJECT_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            self.assertEqual(
                list(Path(temp_home).rglob("*.log")),
                []
            )


    def test_live_log_panel_has_manual_actions(self):
        source = (
            PROJECT_ROOT / "main.py"
        ).read_text(encoding="utf-8")

        for label in (
            '"Copy all"',
            '"Save as..."',
            '"Clear"'
        ):
            self.assertIn(label, source)

        for method in (
            "def _copy_live_log",
            "def _save_live_log",
            "def _clear_live_log"
        ):
            self.assertIn(method, source)


    def test_live_log_save_is_explicit_and_uses_visible_text(self):
        source = (
            PROJECT_ROOT / "main.py"
        ).read_text(encoding="utf-8")

        self.assertIn('"Save Live Log"', source)
        self.assertIn("QFileDialog.getSaveFileName", source)
        self.assertIn("self.log_output.toPlainText()", source)
        self.assertIn("target_path.write_text", source)
        self.assertNotIn("LOG_DIR", source)


    def test_launch_worker_forwards_structured_progress(self):
        source = (
            PROJECT_ROOT / "main.py"
        ).read_text(encoding="utf-8")

        self.assertIn("progress = Signal(str, str)", source)
        self.assertIn("progress_callback=self._report_progress", source)
        self.assertIn("self.session_worker.progress.connect", source)
        self.assertIn("self._session_progress", source)


    def test_session_progress_contains_required_launch_transitions(self):
        source = (
            PROJECT_ROOT / "core" / "session_manager.py"
        ).read_text(encoding="utf-8")

        required = (
            "Starting {game.name} through Steam",
            "Waiting for the actual game executable to remain stable",
            "for 5 seconds",
            "Game executable stable:",
            "PID {runtime.game_pid}",
            "Waiting {trainer_delay} seconds",
            "Starting the trainer inside the running game prefix",
            '"Trainer started."'
        )

        for fragment in required:
            self.assertIn(fragment, source)


    def test_about_no_longer_offers_automatic_log_folder(self):
        source = (
            PROJECT_ROOT / "about_dialog.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("Open Log Folder", source)
        self.assertNotIn("LOG_DIR", source)


    def test_active_user_docs_point_to_live_log_not_automatic_log_path(self):
        paths = (
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "docs" / "TROUBLESHOOTING.md",
            PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml"
        )

        for path in paths:
            source = path.read_text(encoding="utf-8")
            self.assertNotIn(
                "~/.local/share/TrainerBridge/logs/",
                source,
                msg=str(path)
            )

        troubleshooting = paths[1].read_text(encoding="utf-8")
        self.assertIn("does not create persistent log files automatically", troubleshooting)
        self.assertIn("Copy all", troubleshooting)
        self.assertIn("Save as...", troubleshooting)


if __name__ == "__main__":
    unittest.main(verbosity=2)
