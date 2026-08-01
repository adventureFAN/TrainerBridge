# TrainerBridge Beta Test Checklist

## Package startup

- [ ] AppImage starts normally
- [ ] AppImage starts with `APPIMAGE_EXTRACT_AND_RUN=1`
- [ ] Portable `.tar.xz` version starts
- [ ] Icon and About dialog are displayed correctly
- [ ] Main, About and Prefix Components window positions are restored

## Main window

- [ ] Window size and splitter position are restored
- [ ] Search text and status filter are restored
- [ ] Live Log visibility is restored
- [ ] Last selected game is restored

## Game and trainer launch

- [ ] Launch Game + Trainer works
- [ ] Launch Game enables Launch Trainer after verification
- [ ] Launch Trainer works for an already verified game
- [ ] Trainer exits normally with code 0
- [ ] Early non-zero trainer exit shows the runtime-components hint
- [ ] Direct game launch works
- [ ] Publisher-launcher game works

## Prefix Components

- [ ] Native or Flatpak Protontricks is detected
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
