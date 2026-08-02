# Contributing to TrainerBridge

Thanks for helping improve TrainerBridge.

## Bug reports

Use the GitHub bug report template and provide enough detail to reproduce the problem. Logs are most useful when they include the complete launch or Prefix Components attempt, but remove personal paths or other private data when necessary.

Do not attach trainer executables, game files, save files, complete Proton prefixes, or copyrighted material.

## Development setup

TrainerBridge currently targets Python 3.10 or newer.

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements-build.txt
python main.py
```

## Required checks

Before opening a pull request:

```bash
python -m py_compile \
  main.py \
  about_dialog.py \
  options_dialog.py \
  components_dialog.py \
  core/*.py

QT_QPA_PLATFORM=offscreen python main.py --self-test
```

For packaging changes, also run:

```bash
./scripts/build_appimage.sh
```

## Pull requests

- Keep changes focused and explain the user-visible behavior.
- Preserve the existing English user interface.
- Avoid new dependencies unless they are necessary and documented.
- Keep native Steam, Steam Snap, and Steam Flatpak paths separate where their behavior differs.
- Include distribution, Steam package type, Proton version, and filesystem details for platform-specific fixes.
- Update README, troubleshooting, release notes, or changelog when behavior changes.
- Do not weaken prefix-backup or deletion warnings.

By contributing code, you agree that your contribution may be distributed under the project's MIT License.
