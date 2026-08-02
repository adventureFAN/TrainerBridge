#!/usr/bin/env python3
from __future__ import annotations

import importlib.metadata
import shutil
import sys
from pathlib import Path


def is_license_file(relative_path: Path) -> bool:
    lower_parts = [part.lower() for part in relative_path.parts]
    name = relative_path.name.lower()

    if "licenses" in lower_parts or "license" in lower_parts:
        return True

    return (
        name.startswith("license")
        or name.startswith("copying")
        or name.startswith("notice")
        or name.startswith("copyright")
    )


def safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "._-" else "_" for character in value)


def copy_distribution_licenses(distribution_name: str, output_root: Path) -> int:
    try:
        distribution = importlib.metadata.distribution(distribution_name)
    except importlib.metadata.PackageNotFoundError:
        print(f"Warning: distribution not installed: {distribution_name}", file=sys.stderr)
        return 0

    destination_root = output_root / safe_name(distribution.metadata.get("Name", distribution_name))
    copied = 0

    for relative in distribution.files or ():
        relative_path = Path(str(relative))
        if not is_license_file(relative_path):
            continue

        source = Path(distribution.locate_file(relative))
        if not source.is_file():
            continue

        destination = destination_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied += 1

    if copied == 0:
        print(
            f"Warning: no packaged license files found for {distribution_name}",
            file=sys.stderr,
        )

    return copied


def copy_python_license_files(output_root: Path) -> int:
    copied = 0
    destination = output_root / "Python"

    candidates = [
        Path("/usr/share/doc/python3/copyright"),
        Path("/usr/share/doc/python3.10/copyright"),
        Path("/usr/share/doc/libpython3.10/copyright"),
        Path("/usr/share/doc/libpython3.10-stdlib/copyright"),
    ]

    for source in candidates:
        if not source.is_file():
            continue
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / source.parent.name / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1

    if copied == 0:
        print("Warning: no system Python copyright file was found.", file=sys.stderr)

    return copied


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: collect_licenses.py OUTPUT_DIRECTORY", file=sys.stderr)
        return 2

    output_root = Path(sys.argv[1]).resolve()
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True)

    total = copy_python_license_files(output_root)

    for distribution_name in (
        "PySide6",
        "PySide6_Essentials",
        "PySide6_Addons",
        "shiboken6",
        "vdf",
        "zstandard",
        "PyInstaller",
    ):
        total += copy_distribution_licenses(distribution_name, output_root)

    print(f"Collected {total} third-party license file(s) into {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
