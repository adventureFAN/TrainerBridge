#!/usr/bin/env python3
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VersionMetadataTests(unittest.TestCase):

    def test_core_version_has_one_runtime_version_constant(self):
        text = (ROOT / "core/version.py").read_text(encoding="utf-8")
        assignments = re.findall(r"^APP_[A-Z_]*VERSION\s*=", text, flags=re.MULTILINE)
        self.assertEqual(assignments, ["APP_VERSION ="])
        self.assertNotIn("APP_DISPLAY_VERSION", text)

    def test_about_uses_app_version_directly(self):
        text = (ROOT / "about_dialog.py").read_text(encoding="utf-8")
        self.assertIn("APP_VERSION", text)
        self.assertIn('f"Version {APP_VERSION}"', text)
        self.assertNotIn("APP_DISPLAY_VERSION", text)

    def test_main_uses_app_version_for_qt_and_self_test(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("application.setApplicationVersion(\n            APP_VERSION\n        )", text)
        self.assertNotIn("APP_DISPLAY_VERSION", text)

    def test_source_desktop_has_no_hard_coded_appimage_version(self):
        text = (ROOT / "packaging/trainerbridge.desktop").read_text(encoding="utf-8")
        self.assertNotIn("X-AppImage-Version=", text)

    def test_build_version_is_read_from_core_version(self):
        text = (ROOT / "scripts/build_inside_container.sh").read_text(encoding="utf-8")
        self.assertIn("from core.version import APP_VERSION; print(APP_VERSION)", text)
        self.assertIn('APPIMAGE_NAME="${APP_NAME}-${VERSION}-${ARCHITECTURE}.AppImage"', text)
        self.assertIn('ARCHIVE_NAME="${APP_NAME}-${VERSION}-${ARCHITECTURE}.tar.xz"', text)

    def test_build_injects_same_version_into_staged_desktop(self):
        text = (ROOT / "scripts/build_inside_container.sh").read_text(encoding="utf-8")
        self.assertIn("X-AppImage-Version=%s", text)
        self.assertIn('"$VERSION" >> "$APPDIR/trainerbridge.desktop"', text)
        self.assertIn('cp "$APPDIR/trainerbridge.desktop" "$APPDIR/usr/share/applications/trainerbridge.desktop"', text)

    def test_living_install_docs_use_version_placeholder(self):
        for relative_path in (
            "README.md",
            "docs/BUILDING.md",
            "docs/TROUBLESHOOTING.md",
        ):
            text = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertNotIn("TrainerBridge-1.0.0-x86_64", text, relative_path)

    def test_bug_report_placeholder_does_not_pin_release_number(self):
        text = (ROOT / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text(encoding="utf-8")
        self.assertNotIn('placeholder: "1.0.0 AppImage"', text)



if __name__ == "__main__":
    unittest.main(verbosity=2)
