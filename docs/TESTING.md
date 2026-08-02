# Testing TrainerBridge

## Package startup

- [ ] AppImage starts normally.
- [ ] AppImage starts with `APPIMAGE_EXTRACT_AND_RUN=1`.
- [ ] Portable `.tar.xz` version starts.
- [ ] Icon and About dialog are displayed correctly.
- [ ] System, Light, and Dark themes persist after restart.
- [ ] Open Data, Trainers, Trainer, Game, Prefix, Backup, and Log Folder work.
- [ ] Main, Options, About, and Prefix Components window state is restored where supported by the window manager.

## Game and trainer launch

- [ ] Launch Game + Trainer works with a native Steam package.
- [ ] Launch Game + Trainer works with Steam Snap.
- [ ] Steam Flatpak permission prompt grants read-only trainer access.
- [ ] Steam Flatpak detects the running AppID session and launches the trainer.
- [ ] Exported native, Snap, and Flatpak scripts launch correctly.
- [ ] Launch Game enables Launch Trainer after verification.
- [ ] Launch Trainer works for an already verified game.
- [ ] Trainer exits normally with code 0.
- [ ] Early non-zero trainer exit shows the runtime-components hint.
- [ ] Publisher-launcher games are not confused with the actual game executable.

## Prefix Components

- [ ] Native or Flatpak Protontricks is detected.
- [ ] Existing backup can be kept while installing more components.
- [ ] Replace and Delete Backup warnings mention local saves and irreversible loss.
- [ ] Component catalog loads and installed components are shown correctly.
- [ ] Multiple components can be installed.
- [ ] `--no-bwrap` fallback works when required.
- [ ] Restore is verified before replacing the active compatdata directory.
- [ ] Restore followed by Delete Backup leaves TrainerBridge running.

## Distribution record

For every test system, record:

- distribution and version;
- desktop environment and display protocol;
- Steam package type;
- Proton version;
- Protontricks package type and version;
- Steam-library filesystem and mount path;
- AppImage or portable archive.
