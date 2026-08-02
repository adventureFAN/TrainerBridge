# Changelog

All notable changes to TrainerBridge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
