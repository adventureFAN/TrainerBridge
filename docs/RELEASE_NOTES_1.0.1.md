## TrainerBridge 1.0.1

TrainerBridge 1.0.1 is a maintenance and hardening release focused on reliability, diagnostics, packaging, and edge cases found during extensive post-release testing.

### Highlights

- Redesigned **Live Log** with timestamps and clear `OK`, `INFO`, `WARNING`, and `ERROR` levels.
- Added **Copy all**, **Save as...**, and **Clear** actions to the Live Log.
- Normal application use no longer creates persistent log files automatically.
- All TrainerBridge-owned windows now use defined, non-resizable sizes.
- Added per-user **single-instance protection**.
- Improved launch, cancellation, and game/trainer lifecycle handling.
- Added additional security hardening for Steam metadata and exported scripts.
- Improved AppImage build reproducibility and release privacy checks.

### Fixes and reliability improvements

- Fixed a possible Qt thread shutdown issue when closing TrainerBridge during an active launch sequence.
- Steam AppIDs are now matched exactly instead of by substring.
- Exported native/Snap launch scripts now verify the actual Windows game executable and stable PID before starting the trainer.
- Protontricks discovery and read-only catalog queries now use bounded timeouts without freezing the GUI.
- Fixed a session lifecycle issue where closing the game before its TrainerBridge-launched trainer could prevent another game from being launched.
- Trainers started by TrainerBridge are now cleanly stopped when their associated game exits.
- Improved cancellation handling while keeping the game running.
- Runtime and build version metadata now comes from one `APP_VERSION` source.

### Security hardening

- Steam manifest AppIDs are restricted to ASCII digits before they can influence trainer, backup, Proton-prefix, launch, or export paths.
- Invalid or unsafe Steam `installdir` values no longer produce an **Open Game Folder** target.
- Exported Bash scripts no longer interpolate the Steam game name into a comment line, closing a newline-based shell-injection edge case while keeping `GAME_NAME` safely shell-quoted.
- Release checks prevent developer-specific absolute home paths from leaking into TrainerBridge-owned packaged text files.

### Build and packaging

- Updated to the maintained `AppImage/appimagetool` project.
- Pinned `appimagetool` to version 1.9.1 for reproducible builds.
- Fixed a `pipefail`/SIGPIPE issue that could prematurely stop the AppImage build.
- Improved build-time privacy checks while correctly ignoring upstream build paths embedded in third-party binaries such as Qt.
- Expanded automated regression coverage to 96 tests before release.

### Downloads

- **TrainerBridge-1.0.1-x86_64.AppImage** — recommended.
- **TrainerBridge-1.0.1-x86_64.tar.xz** — portable directory version.

SHA-256 checksum files are provided for both packages.
