# TrainerBridge final feature update

This update completes the planned feature set before the 1.0 bug-fixing phase.

## Safety

- complete safety backups of `steamapps/compatdata/<AppID>` before component installation;
- one backup per game, replaced atomically only after a new backup succeeds;
- automatic copy-on-write folder backups when supported;
- compressed `.tar.zst` backups otherwise, with manual method selection in Options;
- visible progress for backup creation and restore;
- restore and delete controls inside Prefix Components;
- transactional restore that keeps the current compatdata directory until the backup has been prepared and verified;
- direct Windows-version detection from `user.reg`, avoiding broken Flatpak custom commands;
- Windows-version restoration is verified after component installation.

## Interface

- complete File, Game, View, Tools, and Help menus;
- keyboard shortcuts and a Shift+F10 game context menu;
- dynamic Import Trainer / Replace Trainer labels;
- trainer removal, folder-opening actions, and launch-script export;
- Options for theme, backup behavior, backup storage method, optional notices, and window geometry;
- System, Light, and Dark themes;
- Live Log moved to the View menu;
- search, status filter, and Rescan on one line;
- simplified window titles using normal hyphens.

## Packaging

- `zstandard==0.25.0` is bundled for compressed backups;
- the frozen self-test verifies that zstandard is available.
