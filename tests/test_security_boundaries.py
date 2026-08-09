from __future__ import annotations

import contextlib
import io
import os
import shlex
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Keep core.paths import-time directory creation away from the real user home.
_TEST_HOME = tempfile.TemporaryDirectory()
_ORIGINAL_HOME = os.environ.get("HOME")
os.environ["HOME"] = _TEST_HOME.name

try:
    import vdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["vdf"] = types.ModuleType("vdf")

from core import backup_manager, games, storage
from core.exporter import _build_flatpak_script, _build_standard_script
from core.game_launcher import SteamGameLauncher
from core.models import GameProfile
from core.protontricks import ProtontricksManager
from core.validation import (
    build_steam_game_path,
    validate_steam_appid,
    validate_steam_install_dir,
)

if _ORIGINAL_HOME is None:
    os.environ.pop("HOME", None)
else:
    os.environ["HOME"] = _ORIGINAL_HOME


class SteamManifestValidationTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.library = self.root / "SteamLibrary"
        self.steamapps = self.library / "steamapps"
        self.steamapps.mkdir(parents=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def write_manifest(self, name="appmanifest_123.acf"):
        manifest = self.steamapps / name
        manifest.write_text("placeholder", encoding="utf-8")
        return manifest

    def test_valid_appids_are_normalized(self):
        self.assertEqual(validate_steam_appid("1173770"), "1173770")
        self.assertEqual(validate_steam_appid(1173770), "1173770")

    def test_unsafe_appids_are_rejected(self):
        for value in (
            "",
            "/etc",
            "../../.ssh",
            "123/456",
            "123\n456",
            "１２３",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_steam_appid(value)

    def test_game_profile_rejects_invalid_appid(self):
        with self.assertRaises(ValueError):
            GameProfile(
                name="Unsafe",
                appid="../../escape",
                library=self.library,
            )

    def test_safe_install_dir_builds_inside_steam_common(self):
        self.assertEqual(
            validate_steam_install_dir("Test Game"),
            "Test Game",
        )
        self.assertEqual(
            build_steam_game_path(self.library, "Test Game"),
            self.library / "steamapps" / "common" / "Test Game",
        )

    def test_unsafe_install_dirs_are_rejected(self):
        for value in (
            "/etc",
            "../escape",
            "nested/escape",
            ".",
            "..",
            "",
            "bad\x00name",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_steam_install_dir(value)

    def test_scanner_skips_manifest_with_invalid_appid(self):
        self.write_manifest()

        with mock.patch.object(
            games.vdf,
            "load",
            return_value={
                "AppState": {
                    "appid": "../../escape",
                    "name": "Unsafe Game",
                    "installdir": "Unsafe Game",
                }
            },
            create=True,
        ), contextlib.redirect_stdout(io.StringIO()):
            found = games.find_games([self.library])

        self.assertEqual(found, [])

    def test_scanner_disables_game_folder_for_unsafe_installdir(self):
        self.write_manifest()

        with mock.patch.object(
            games.vdf,
            "load",
            return_value={
                "AppState": {
                    "appid": "123",
                    "name": "Test Game",
                    "installdir": "../../outside",
                }
            },
            create=True,
        ), contextlib.redirect_stdout(io.StringIO()):
            found = games.find_games([self.library])

        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].appid, "123")
        self.assertIsNone(found[0].game_path)


class DestructivePathBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.trainer_dir = self.root / "trainers"
        self.config_file = self.root / "trainers.json"
        self.data_dir = self.root / "data"
        self.legacy_data_dir = self.root / "legacy"
        self.backup_dir = self.root / "backups"

    def tearDown(self):
        self.tempdir.cleanup()

    def storage_patches(self):
        return (
            mock.patch.object(storage, "TRAINER_DIR", self.trainer_dir),
            mock.patch.object(storage, "CONFIG_FILE", self.config_file),
            mock.patch.object(storage, "DATA_DIR", self.data_dir),
            mock.patch.object(storage, "LEGACY_DATA_DIR", self.legacy_data_dir),
        )

    def test_import_trainer_rejects_path_traversal_appid(self):
        source = self.root / "trainer.exe"
        source.write_bytes(b"trainer")
        escaped = self.root / "escaped"

        patches = self.storage_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(ValueError):
                storage.import_trainer("../escaped", source)

        self.assertFalse(escaped.exists())

    def test_remove_trainer_cannot_delete_outside_trainer_root(self):
        escaped = self.root / "escaped"
        escaped.mkdir()
        sentinel = escaped / "keep.txt"
        sentinel.write_text("keep", encoding="utf-8")

        patches = self.storage_patches()
        with patches[0], patches[1], patches[2], patches[3]:
            with self.assertRaises(ValueError):
                storage.remove_trainer("../escaped")

        self.assertTrue(sentinel.is_file())

    def test_backup_manager_rejects_invalid_appid_before_path_setup(self):
        game = SimpleNamespace(
            appid="../../escape",
            name="Unsafe Game",
            prefix=None,
            library=self.root / "library",
        )

        with mock.patch.object(backup_manager, "BACKUP_DIR", self.backup_dir):
            with self.assertRaises(ValueError):
                backup_manager.BackupManager(game)

        self.assertFalse((self.root / "escape").exists())


class SecondaryAppIdBoundaryTests(unittest.TestCase):
    def test_game_launcher_rejects_invalid_appid_before_building_uri(self):
        with self.assertRaises(ValueError):
            SteamGameLauncher().build_command("../../escape")

    def test_protontricks_prefix_lookup_rejects_invalid_appid(self):
        manager = ProtontricksManager(
            SimpleNamespace(command_prefix=("protontricks",))
        )

        with self.assertRaises(ValueError):
            manager._find_prefix_path("/etc")


class ExportedScriptInjectionTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.marker = self.root / "injected"
        self.game = SimpleNamespace(
            appid="123",
            name=(
                "Safe Game\n"
                f"printf injected > {shlex.quote(str(self.marker))}\n"
                "#"
            ),
            prefix=self.root / "compatdata" / "123",
            trainer_path=self.root / "trainer.exe",
        )
        self.proton = self.root / "proton"
        self.steam_info = {
            "install_path": str(self.root / "steam"),
            "launch_prefix": ("/usr/bin/true",),
        }

    def tearDown(self):
        self.tempdir.cleanup()

    def run_header_only(self, script, boundary):
        header = script.split(boundary, 1)[0]
        script_path = self.root / "header.sh"
        script_path.write_text(header + "\nexit 0\n", encoding="utf-8")
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            self.marker.exists(),
            "a newline in the game name executed shell code from the exported header",
        )

    def test_standard_exporter_does_not_execute_game_name_from_comment(self):
        script = _build_standard_script(
            self.game,
            self.steam_info,
            self.proton,
        )
        self.assertIn("# Exported by TrainerBridge.\n", script)
        self.assertNotIn("# Exported by TrainerBridge for ", script)
        self.run_header_only(script, "command -v python3")

    def test_flatpak_exporter_does_not_execute_game_name_from_comment(self):
        script = _build_flatpak_script(
            self.game,
            self.steam_info,
            self.proton,
        )
        self.assertIn("# Exported by TrainerBridge.\n", script)
        self.assertNotIn("# Exported by TrainerBridge for ", script)
        self.run_header_only(script, "command -v flatpak")

    def test_exporter_rejects_invalid_appid_even_for_synthetic_game(self):
        self.game.appid = "../../escape"

        with self.assertRaises(ValueError):
            _build_standard_script(
                self.game,
                self.steam_info,
                self.proton,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
