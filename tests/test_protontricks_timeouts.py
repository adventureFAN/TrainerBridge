import ast
import subprocess
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import vdf  # noqa: F401
except ModuleNotFoundError:
    sys.modules["vdf"] = types.ModuleType("vdf")

from core.protontricks import (
    ProtontricksError,
    ProtontricksInstallation,
    ProtontricksManager,
)


class ProtontricksTimeoutTests(unittest.TestCase):

    def make_manager(self):
        return ProtontricksManager(
            ProtontricksInstallation(
                kind="native",
                command_prefix=("protontricks",),
                display_name="System installation",
            )
        )

    def test_flatpak_detection_is_bounded(self):
        def fake_which(name):
            if name == "protontricks":
                return None
            if name == "flatpak":
                return "/usr/bin/flatpak"
            return None

        with patch("core.protontricks.shutil.which", side_effect=fake_which), patch(
            "core.protontricks.subprocess.run",
            return_value=SimpleNamespace(returncode=1),
        ) as run_mock:
            self.assertIsNone(ProtontricksManager.detect())

        self.assertEqual(run_mock.call_args.kwargs.get("timeout"), 5)

    def test_flatpak_detection_timeout_becomes_clear_protontricks_error(self):
        def fake_which(name):
            if name == "protontricks":
                return None
            if name == "flatpak":
                return "/usr/bin/flatpak"
            return None

        def timeout_run(command, **kwargs):
            raise subprocess.TimeoutExpired(command, kwargs.get("timeout"))

        with patch("core.protontricks.shutil.which", side_effect=fake_which), patch(
            "core.protontricks.subprocess.run",
            side_effect=timeout_run,
        ):
            with self.assertRaises(ProtontricksError) as caught:
                ProtontricksManager.detect()

        self.assertIn("Flatpak did not respond within 5 seconds", str(caught.exception))

    def test_version_query_uses_read_only_timeout(self):
        manager = self.make_manager()
        manager._run_capture = Mock(return_value="protontricks 1.13.0")

        self.assertEqual(manager.get_version(), "protontricks 1.13.0")
        self.assertEqual(manager._run_capture.call_args.kwargs.get("timeout"), 30)

    def test_catalog_queries_use_read_only_timeout(self):
        manager = self.make_manager()
        manager._run_capture = Mock(return_value="")

        manager.list_installed(123)
        installed_call = manager._run_capture.call_args
        self.assertEqual(installed_call.kwargs.get("timeout"), 30)

        manager.list_category(123, "dlls")
        category_call = manager._run_capture.call_args
        self.assertEqual(category_call.kwargs.get("timeout"), 30)

    def test_read_only_timeout_is_reported_as_protontricks_error(self):
        manager = self.make_manager()
        manager._build_environment = Mock(return_value={})

        def timeout_run(command, **kwargs):
            raise subprocess.TimeoutExpired(
                command,
                kwargs.get("timeout"),
                output=b"partial stdout",
                stderr=b"partial stderr",
            )

        with patch("core.protontricks.subprocess.run", side_effect=timeout_run):
            with self.assertRaises(ProtontricksError) as caught:
                manager._execute_capture(
                    arguments=("--version",),
                    force_english=True,
                    no_bwrap=False,
                    timeout=30,
                )

        message = str(caught.exception)
        self.assertIn("did not finish within 30 seconds", message)
        self.assertIn("partial stdout", message)
        self.assertIn("partial stderr", message)

    def test_prefix_installation_intentionally_has_no_timeout(self):
        manager = self.make_manager()
        manager.game_is_running = Mock(return_value=False)
        manager.get_windows_version = Mock(return_value="win10")
        manager.set_windows_version = Mock(return_value="")
        manager._run_capture = Mock(return_value="installed")

        manager.install_components_capture(123, ("vcrun2022",))

        install_call = manager._run_capture.call_args
        self.assertEqual(install_call.args, ("123", "vcrun2022"))
        self.assertEqual(install_call.kwargs, {"force_english": False})


class PrefixComponentsThreadingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.source_path = PROJECT_ROOT / "components_dialog.py"
        cls.source = cls.source_path.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def find_method(self, class_name, method_name):
        for node in self.tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == method_name:
                        return child
        self.fail(f"Could not find {class_name}.{method_name}")

    def test_dialog_constructor_does_not_detect_protontricks_synchronously(self):
        constructor = self.find_method("ComponentsDialog", "__init__")

        for node in ast.walk(constructor):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if (
                isinstance(function, ast.Attribute)
                and function.attr == "detect"
                and isinstance(function.value, ast.Name)
                and function.value.id == "ProtontricksManager"
            ):
                self.fail("ComponentsDialog.__init__ still calls ProtontricksManager.detect() synchronously")

    def test_detection_uses_dedicated_qthread_worker(self):
        worker = next(
            (
                node
                for node in self.tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "ProtontricksDetectWorker"
            ),
            None,
        )
        self.assertIsNotNone(worker, "ProtontricksDetectWorker is missing")

        start_method = self.find_method("ComponentsDialog", "_start_protontricks_detection")
        names = {
            node.id
            for node in ast.walk(start_method)
            if isinstance(node, ast.Name)
        }
        self.assertIn("QThread", names)
        self.assertIn("ProtontricksDetectWorker", names)


if __name__ == "__main__":
    unittest.main(verbosity=2)
