# TrainerBridge 1.0.0

TrainerBridge 1.0.0 is the first stable release of the Linux GUI for launching standalone Windows trainers alongside Steam games running through Proton.

## Highlights

- Automatic Steam-library, Proton-version, prefix, and game-executable detection.
- Combined game and trainer launch with verified session monitoring.
- Native Steam, Steam Snap, and Steam Flatpak support.
- Tested Steam Flatpak trainer launch using the live environment of the matching game sandbox.
- Standalone exported launch scripts for all three Steam package types.
- Optional Prefix Components management through native or Flatpak Protontricks.
- Verified safety backups and transactional restore.
- Btrfs copy-on-write and compressed Zstandard backup methods.
- System, Light, and Dark themes with persistent UI state.
- AppImage and portable `.tar.xz` packages with SHA-256 checksums.

## Tested during development

- Bazzite and Fedora Workstation
- Ubuntu
- Linux Mint
- CachyOS
- native Steam, Snap, and Flatpak
- official Proton and GE-Proton
- native and Flatpak Protontricks

Other distributions and configurations may work but have not all been tested.

## Important notes

- Trainers are not included.
- Only use trainer executables from sources you trust.
- Do not use trainers in online or competitive multiplayer games.
- TrainerBridge does not bypass anti-cheat systems.
- Prefix modifications and backup deletion can affect local save files and other compatdata-only data.
- Component and trainer compatibility cannot be guaranteed for every game or Proton version.

## Downloads

Recommended:

- `TrainerBridge-1.0.0-x86_64.AppImage`

FUSE-free fallback:

- `TrainerBridge-1.0.0-x86_64.tar.xz`

Verify either download with its matching `.sha256` file.

Full changes are listed in [CHANGELOG.md](https://github.com/adventureFAN/TrainerBridge/blob/v1.0.0/CHANGELOG.md).
