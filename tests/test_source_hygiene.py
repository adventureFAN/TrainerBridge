from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENTS_DIALOG = ROOT / "components_dialog.py"


class SourceHygieneTests(unittest.TestCase):
    def test_old_patch_note_files_are_removed(self):
        obsolete = (
            ROOT / "APPLY_NOTES.md",
            ROOT / "FLATPAK_RUNTIME_FIX_NOTES.md",
        )
        existing = [path.name for path in obsolete if path.exists()]
        self.assertEqual(existing, [], f"obsolete patch notes still present: {existing}")


    def test_no_one_off_before_step_snapshots_remain(self):
        snapshots = sorted(ROOT.rglob("*.before-step*"))
        self.assertEqual(
            snapshots,
            [],
            "one-off before-step snapshots must not ship in the public source tree",
        )

    def test_no_developer_identity_or_absolute_home_path_is_hardcoded(self):
        personal_identifier = "al" + "ex"
        home_pattern = re.compile(r"/(?:var/)?home/[A-Za-z0-9._-]+/")
        hits: list[str] = []

        excluded_dirs = {".git", "venv", ".build-venv", "build", "dist", "release", "TrainerBridge.AppDir", "tools", "__pycache__"}
        excluded_suffixes = {".pyc", ".png", ".svg", ".AppImage", ".xz", ".zip"}

        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in excluded_dirs for part in path.parts):
                continue
            if path.suffix in excluded_suffixes:
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue

            lowered = text.casefold()
            if personal_identifier in lowered:
                hits.append(f"{path.relative_to(ROOT)} -> developer identifier")

            if "tests" not in path.parts:
                for match in home_pattern.finditer(text):
                    candidate = match.group(0)
                    if "<user>" not in candidate:
                        hits.append(f"{path.relative_to(ROOT)} -> {candidate}")

        self.assertEqual(
            hits,
            [],
            "developer-specific identity/path text remains: " + "; ".join(hits),
        )

    def test_build_rejects_any_absolute_home_path(self):
        source = (ROOT / "scripts" / "build_inside_container.sh").read_text(encoding="utf-8")
        self.assertIn("/(var/)?home/[^/[:space:]]+", source)
        self.assertNotIn('"/home/' + 'al' + 'ex"', source)

    def test_build_privacy_scan_ignores_third_party_binary_build_paths(self):
        source = (ROOT / "scripts" / "build_inside_container.sh").read_text(encoding="utf-8")
        self.assertIn("grep -R -I -E -l", source)
        self.assertNotIn("grep -R -a -E -l '/(var/)?home/", source)
        self.assertIn("Third-party ELF binaries", source)
        self.assertIn("staged text files", source)

    def test_no_consecutive_duplicate_slot_decorators_remain(self):
        source = COMPONENTS_DIALOG.read_text(encoding="utf-8")
        duplicate = re.compile(
            r"(?m)^(?P<indent>\s*)@Slot\((?P<args>[^\n]*)\)\s*\n"
            r"(?P=indent)@Slot\((?P=args)\)\s*$"
        )
        self.assertIsNone(
            duplicate.search(source),
            "components_dialog.py still contains consecutive duplicate @Slot decorators",
        )

    def test_components_loaded_keeps_one_object_slot(self):
        source = COMPONENTS_DIALOG.read_text(encoding="utf-8")
        match = re.search(
            r"(?m)(?P<decorators>(?:\s*@Slot\([^\n]*\)\s*\n)+)"
            r"\s*def _components_loaded\(",
            source,
        )
        self.assertIsNotNone(match, "_components_loaded slot declaration not found")
        decorators = re.findall(r"@Slot\(([^\n]*)\)", match.group("decorators"))
        self.assertEqual(decorators, ["object"])

    def test_old_note_filenames_are_not_referenced_by_runtime_or_packaging_source(self):
        names = ("APPLY_NOTES.md", "FLATPAK_RUNTIME_FIX_NOTES.md")
        searchable_roots = (
            ROOT / "main.py",
            ROOT / "components_dialog.py",
            ROOT / "core",
            ROOT / "packaging",
            ROOT / "scripts",
            ROOT / ".github",
        )
        hits: list[str] = []
        for item in searchable_roots:
            paths = [item] if item.is_file() else [p for p in item.rglob("*") if p.is_file()]
            for path in paths:
                if "__pycache__" in path.parts or path.suffix in {".pyc", ".png", ".svg"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for name in names:
                    if name in text:
                        hits.append(f"{path.relative_to(ROOT)} -> {name}")
        self.assertEqual(
            hits,
            [],
            "obsolete patch-note references remain in runtime/packaging source: " + "; ".join(hits),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
