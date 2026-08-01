# TrainerBridge 0.9.0 Beta 1 — AppImage build

## One-command build

From the TrainerBridge project folder:

```bash
./scripts/build_appimage.sh
```

The first build creates an isolated `.build-venv`, installs the build tools,
downloads `appimagetool`, and creates:

```text
release/TrainerBridge-0.9.0-beta.1-x86_64.AppImage
```

Run it with:

```bash
./release/TrainerBridge-0.9.0-beta.1-x86_64.AppImage
```

The build can take several minutes the first time. Later builds reuse the
build environment and downloaded AppImage tool.

## AppImage runtime dependencies

TrainerBridge bundles Python, PySide6, Qt and the Python `vdf` module.
It intentionally does not bundle Steam, Proton or Protontricks. Those must be
available on the host system.

## Saved UI state

The main window now remembers:

- window size and position
- maximized/full-screen state
- splitter position
- status filter
- search text
- selected Steam AppID

Qt stores these desktop preferences in the normal per-user settings location.
Trainer files, caches and logs remain under:

```text
~/.local/share/TrainerBridge/
```

## Logs

Each launch creates a log file under:

```text
~/.local/share/TrainerBridge/logs/
```

Use **Help → About TrainerBridge → Open Log Folder**.
