# TrainerBridge 1.0 RC1 Test Checklist

## Package startup

- [ ] AppImage starts normally
- [ ] AppImage starts with `APPIMAGE_EXTRACT_AND_RUN=1`
- [ ] Portable `.tar.xz` version starts
- [ ] Icon and About dialog are displayed correctly
- [ ] System, Light and Dark themes persist after restart
- [ ] Open Data, Trainers, Trainer, Game, Prefix, Backup and Log Folder work
- [ ] Main, Options, About and Prefix Components window sizes/positions are restored where supported by the window manager

## Main window

- [ ] Window size and splitter position are restored
- [ ] Search text and status filter are restored
- [ ] Live Log visibility is restored
- [ ] Last selected game is restored

## Game and trainer launch

- [ ] Launch Game + Trainer works
- [ ] Steam Flatpak permission prompt grants read-only trainer access
- [ ] Steam Flatpak detects the running AppID session and launches the trainer
- [ ] Exported Steam Flatpak launch script detects the session and launches the trainer
- [ ] Launch Game enables Launch Trainer after verification
- [ ] Launch Trainer works for an already verified game
- [ ] Trainer exits normally with code 0
- [ ] Early non-zero trainer exit shows the runtime-components hint
- [ ] Direct game launch works
- [ ] Publisher-launcher game works

## Prefix Components

- [ ] Native or Flatpak Protontricks is detected
- [ ] Existing backup can be kept while installing more components
- [ ] Replace and Delete Backup warnings mention local saves and irreversible loss
- [ ] Component catalog loads
- [ ] Installed components are shown correctly
- [ ] Multiple components can be installed
- [ ] `--no-bwrap` fallback works when required
- [ ] Game and AppID appear only under Show technical details
- [ ] Prefix Components window position is restored
- [ ] Output visibility is restored

## Distribution matrix

Record for every test system:

- Distribution and version
- Desktop environment
- Steam package type: native, Flatpak or Snap
- Proton version
- Protontricks package type and version
- Game library filesystem and mount path
