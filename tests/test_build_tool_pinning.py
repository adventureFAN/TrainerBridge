#!/usr/bin/env python3
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts/build_inside_container.sh"


class BuildToolPinningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_uses_maintained_appimagetool_repository(self):
        self.assertIn("https://github.com/AppImage/appimagetool/releases/download/", self.text)
        self.assertNotIn("AppImage/AppImageKit/releases/download", self.text)

    def test_appimagetool_release_is_pinned(self):
        self.assertIsNotNone(
            re.search(r'^APPIMAGETOOL_VERSION="1\.9\.1"$', self.text, re.MULTILINE)
        )
        self.assertNotIn("/continuous/", self.text)

    def test_download_url_uses_pinned_version(self):
        expected = 'APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/${APPIMAGETOOL_VERSION}/appimagetool-${ARCHITECTURE}.AppImage"'
        self.assertIn(expected, self.text)

    def test_cache_filename_contains_pinned_version(self):
        expected = 'APPIMAGETOOL="$TOOLS_DIR/appimagetool-${APPIMAGETOOL_VERSION}-${ARCHITECTURE}.AppImage"'
        self.assertIn(expected, self.text)
        self.assertNotIn('APPIMAGETOOL="$TOOLS_DIR/appimagetool-${ARCHITECTURE}.AppImage"', self.text)

    def test_download_keeps_fail_and_retry_guards(self):
        self.assertIn("--fail", self.text)
        self.assertIn("--location", self.text)
        self.assertIn("--retry 3", self.text)
        self.assertIn('--output "$APPIMAGETOOL"', self.text)

    def test_build_environment_probe_is_pipefail_safe(self):
        safe_probe = "ldd --version 2>&1 | sed -n '1p'"
        self.assertIn(safe_probe, self.text)
        self.assertNotIn("ldd --version | head -n 1", self.text)

        with tempfile.TemporaryDirectory() as tmp:
            fake_ldd = Path(tmp) / "ldd"
            fake_ldd.write_text(
                "#!/bin/sh\n"
                "printf '%s\n' 'fake ldd 1.0'\n"
                "i=0\n"
                "while [ \"$i\" -lt 5000 ]; do\n"
                "    printf '%s\n' 'extra version output'\n"
                "    i=$((i + 1))\n"
                "done\n",
                encoding="utf-8",
            )
            fake_ldd.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = f"{tmp}:{env.get('PATH', '')}"
            result = subprocess.run(
                ["bash", "-c", f"set -euo pipefail; {safe_probe}"],
                text=True,
                capture_output=True,
                env=env,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "fake ldd 1.0")

    def test_build_docs_record_the_pin(self):
        docs = (ROOT / "docs/BUILDING.md").read_text(encoding="utf-8")
        self.assertIn("appimagetool` release **1.9.1**", docs)
        self.assertIn("AppImage/appimagetool", docs)
        self.assertIn("cached tool filename includes that version", docs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
