from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FixedWindowSizeTests(unittest.TestCase):
    def _source(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_main_has_two_defined_fixed_sizes(self):
        source = self._source("main.py")
        self.assertIn("MAIN_WINDOW_SIZE_WITH_LOG = (1220, 800)", source)
        self.assertIn("MAIN_WINDOW_SIZE_WITHOUT_LOG = (1220, 620)", source)
        self.assertIn("self.setFixedSize(", source)

    def test_main_log_visibility_reapplies_fixed_size(self):
        source = self._source("main.py")
        match = re.search(
            r"def _set_log_visible\(.*?(?=\n    def )",
            source,
            re.S,
        )
        self.assertIsNotNone(match)
        self.assertIn("self._apply_fixed_window_size()", match.group(0))

    def test_main_no_longer_uses_resizable_minimum_window_size(self):
        source = self._source("main.py")
        ctor = re.search(r"class MainWindow.*?def _build_interface", source, re.S)
        self.assertIsNotNone(ctor)
        self.assertNotIn("setMinimumSize", ctor.group(0))

    def test_prefix_components_is_fixed_1000_by_700(self):
        source = self._source("components_dialog.py")
        self.assertIn("COMPONENTS_WINDOW_SIZE = (1000, 700)", source)
        self.assertIn("self.setFixedSize(*COMPONENTS_WINDOW_SIZE)", source)
        ctor = re.search(r"class ComponentsDialog.*?def _build_interface", source, re.S)
        self.assertIsNotNone(ctor)
        self.assertNotIn("self.resize(", ctor.group(0))
        self.assertNotIn("setMinimumSize", ctor.group(0))

    def test_options_is_fixed_620_by_460(self):
        source = self._source("options_dialog.py")
        self.assertIn("OPTIONS_WINDOW_SIZE = (620, 460)", source)
        self.assertIn("self.setFixedSize(*OPTIONS_WINDOW_SIZE)", source)
        self.assertNotIn("self.resize(620, 460)", source)
        self.assertNotIn("self.setMinimumSize(560, 420)", source)

    def test_geometry_option_no_longer_claims_sizes_are_remembered(self):
        source = self._source("options_dialog.py")
        self.assertIn("Remember window positions and layout", source)
        self.assertNotIn("Remember window sizes and positions", source)

    def test_about_is_fixed_520_by_500(self):
        source = self._source("about_dialog.py")
        self.assertIn("ABOUT_WINDOW_SIZE = (520, 500)", source)
        self.assertIn("self.setFixedSize(*ABOUT_WINDOW_SIZE)", source)
        self.assertNotIn("self.setFixedWidth(", source)

    def test_third_party_notices_dialog_is_fixed(self):
        source = self._source("about_dialog.py")
        self.assertIn("THIRD_PARTY_WINDOW_SIZE = (720, 560)", source)
        self.assertIn("dialog.setFixedSize(*THIRD_PARTY_WINDOW_SIZE)", source)
        self.assertNotIn("dialog.resize(", source)

    def test_all_custom_top_level_windows_are_covered(self):
        combined = "\n".join(
            self._source(name)
            for name in ("main.py", "components_dialog.py", "options_dialog.py", "about_dialog.py")
        )
        expected_classes = {"MainWindow", "ComponentsDialog", "OptionsDialog", "AboutDialog"}
        discovered = set(re.findall(r"class\s+(\w+)\s*\((?:QMainWindow|QDialog)\)", combined))
        self.assertEqual(discovered, expected_classes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
