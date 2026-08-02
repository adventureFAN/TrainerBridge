# Troubleshooting

## The AppImage does not start

Make it executable:

```bash
chmod +x TrainerBridge-1.0.0-x86_64.AppImage
```

Run without FUSE:

```bash
APPIMAGE_EXTRACT_AND_RUN=1 \
  ./TrainerBridge-1.0.0-x86_64.AppImage
```

## A game is missing

1. Start the game once through Steam.
2. Confirm that Steam created `steamapps/compatdata/<AppID>`.
3. Confirm that the game is forced to use Proton when necessary.
4. Select **Rescan** in TrainerBridge.
5. Check the live log and `~/.local/share/TrainerBridge/logs/`.

## The game starts but the trainer does not

- Wait for TrainerBridge's 60-second detection timeout.
- Confirm that the selected game's Proton version and prefix are shown correctly.
- Confirm that the imported trainer file still exists.
- Try **Launch Trainer** after the game has been verified.
- Check whether the trainer requires .NET, Visual C++ runtimes, fonts, or another component.
- A trainer that works on Windows may still be incompatible with Wine or Proton.

## Steam Flatpak cannot access the trainer

TrainerBridge grants Steam Flatpak read-only access to:

```text
~/.local/share/TrainerBridge/trainers
```

After granting access, completely exit and restart Steam Flatpak. Then retry the launch.

## Prefix Components installation fails

Component installation depends on Proton, Wine, the prefix state, and the Winetricks recipe.

- Keep an existing tested backup when installing additional components.
- Read the Protontricks output in the dialog.
- Some old components require a 32-bit prefix and cannot be installed into a normal 64-bit Proton prefix.
- GE-Proton was the most reliable option during TrainerBridge testing and is worth trying after a failure, but it does not guarantee success.
- Do not delete `compatdata` without considering local save files and settings stored inside the prefix.

## Backup size looks as large as the original prefix

A Btrfs copy-on-write folder reports the full logical size even though most data blocks are initially shared with the original prefix. Additional physical space is mainly consumed when either copy changes.

## Open Folder does nothing

Check that `xdg-open` or `gio` is available and that a graphical file manager is installed. The application log may contain the failed host command.

## Logs and data

```text
~/.local/share/TrainerBridge/logs/
~/.local/share/TrainerBridge/settings.ini
~/.local/share/TrainerBridge/trainers.json
~/.local/share/TrainerBridge/backups/
```

Remove private paths and personal information before posting logs publicly. Never upload trainer binaries, game files, save files, or complete prefixes.
