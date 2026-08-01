# TrainerBridge 0.9.0 Beta 1 — Test checklist

## Test environment

- Distribution and version:
- Desktop environment:
- Wayland or X11:
- Steam installation: system / Flatpak
- Proton version:
- Protontricks installation: system / Flatpak / missing
- Steam library filesystem: Btrfs / ext4 / NTFS / other
- Game AppID:
- Game uses a publisher launcher: yes / no
- Trainer runtime: Win32 / .NET Framework / .NET Core / unknown

## Core tests

- [ ] TrainerBridge starts from the AppImage
- [ ] Steam libraries are detected
- [ ] Native Linux games are shown but marked unsupported
- [ ] Status filter is restored after restarting TrainerBridge
- [ ] Window size and splitter position are restored
- [ ] Trainer import works
- [ ] Launch Game detects the actual game executable
- [ ] Launch Trainer becomes available only after game verification
- [ ] Launch Game + Trainer works
- [ ] Trainer detects the running game
- [ ] Trainer closes cleanly
- [ ] Game closes cleanly after the trainer
- [ ] Prefix Components detects native or Flatpak Protontricks
- [ ] Previously installed components are shown
- [ ] Multiple component installation works
- [ ] Windows compatibility version is preserved
- [ ] Help → About TrainerBridge opens
- [ ] Open Log Folder opens the correct directory

## Launcher tests

Record every intermediate executable shown by the game:

- [ ] Direct game executable
- [ ] Publisher login/update launcher
- [ ] Launcher closes before game executable starts
- [ ] Launcher remains open while the game runs
- [ ] Game executable changes after an update

## Bug report

Please include:

1. The completed environment section above
2. Exact steps to reproduce
3. Expected behavior
4. Actual behavior
5. The newest log from `~/.local/share/TrainerBridge/logs/`
6. Screenshots when the problem is visual
