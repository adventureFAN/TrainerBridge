# Changelog

All notable changes to TrainerBridge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-08-09

### Changed

- Reworked the in-app Live Log with compact timestamps, explicit `OK` / `INFO` / `WARNING` / `ERROR` levels, clearer launch-state transitions, and manual **Copy all**, **Save as...**, and **Clear** actions.
- Normal application use no longer creates persistent log files automatically; user-home paths shown in the Live Log are shortened to `~` before copying or saving.
- TrainerBridge-owned windows now use fixed, non-resizable sizes; the main window switches between two defined heights when the Live Log is shown or hidden.
- Runtime and build version metadata now comes from one `APP_VERSION` source.
- Release tooling now uses pinned `appimagetool` 1.9.1 from the maintained upstream repository.

### Fixed

- Closing TrainerBridge during an active launch now cancels cooperatively and waits for the launch worker to finish, preventing `QThread` destruction while leaving the game running.
- Native/Snap Steam-process detection now requires an exact `AppId=<ID>` argument instead of substring matching.
- Exported native/Snap launch scripts now verify the actual expected Windows game executable and a stable PID before starting the trainer.
- Protontricks discovery and read-only catalog queries now run off the GUI thread with bounded timeouts, preventing hung discovery/query commands from freezing Prefix Components.
- Added per-user single-instance protection so concurrent TrainerBridge processes cannot interfere with prefix-backup recovery state.
- Fixed a release-build abort caused by `ldd --version | head -n 1` under `set -o pipefail` returning SIGPIPE/exit 141.
- Fixed the release privacy gate falsely rejecting upstream build paths embedded in third-party binary libraries such as Qt; staged text content remains checked for absolute user-home paths.
- Removed stale development-note/snapshot files and hardened public-source/release checks against developer-specific absolute home paths.
- Steam manifest AppIDs are now restricted to ASCII digits before they can influence trainer, backup, Proton-prefix, launch, or export paths; unsafe `installdir` values no longer produce an Open Game Folder target.
- Exported Bash scripts no longer interpolate the Steam game name into a comment line, closing a newline-based shell-injection edge case while keeping the quoted `GAME_NAME` variable.
- When a verified game exits before its TrainerBridge-launched trainer, TrainerBridge now stops the trainer process group and releases the active session so another game can be launched without manually closing the old trainer first.

## [1.0.0] - 2026-08-02

### Added

- Steam library scanning across detected library folders.
- Per-game Proton, compatdata, executable, and trainer detection.
- Combined game and trainer launch with verified Proton-session monitoring.
- Separate game-only and trainer-only launch actions.
- Steam native package, Snap, and Flatpak support.
- Steam Flatpak session detection using the matching AppID sandbox and live Steam environment.
- One-time read-only trainer-folder permission handling for Steam Flatpak.
- Standalone exported launch scripts for native Steam, Snap, and Flatpak.
- Prefix Components frontend for native and Flatpak Protontricks.
- Searchable, categorized, multi-select component catalog with installed-state display.
- Safety backups using Btrfs copy-on-write folders or compressed Zstandard archives.
- Verified, transactional restore and explicit backup deletion warnings.
- Backup policies: Ask, Always, and Never.
- Backup storage choices: Automatic, Compressed Archive, and Folder.
- System, Light, and Dark themes with persistent settings.
- Persistent main-window geometry, splitter, search, filter, selection, and log visibility.
- Menus, keyboard shortcuts, context menu, live log, About dialog, and Third-Party Notices.
- Open-folder actions for application data, trainers, trainer, game, prefix, backup, and logs.
- AppImage and portable `.tar.xz` release builds with SHA-256 checksums.

### Changed

- Trainer launch begins four seconds after the Proton session is verified.
- Component failures recommend trying GE-Proton without promising success.
- Backup replacement and deletion dialogs explicitly mention local saves and other compatdata-only data.
- Existing safety backups can be kept while component installation continues without creating a new backup.

### Fixed

- Official Proton version path detection from `config_info`.
- Non-UTF-8 Protontricks output decoding.
- Windows-version detection without unsupported Protontricks shell commands.
- Windows-version restoration after component installation.
- Backup progress values above 2 GiB.
- Compressed restore of valid absolute Wine symlinks.
- Backup worker lifetime issues during Restore followed by Delete.
- Exported-script session detection and `/proc` command-line parsing.
- Steam Snap launch handling.
- Steam Flatpak game detection, environment transfer, trainer launch, and exported scripts.
- Folder opening from AppImage and sanitized host environments.
- Theme persistence and duplicated legacy QSettings General sections.
