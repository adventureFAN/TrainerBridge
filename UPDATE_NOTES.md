# TrainerBridge 1.0 RC1

- Adds tested Steam Flatpak game detection and trainer launch by entering the running game sandbox and copying its live Steam/desktop environment.
- Adds a one-time read-only Steam Flatpak permission prompt for the TrainerBridge trainer folder.
- Keeps native Steam and Steam Snap launch behavior unchanged.
- Reduces the trainer launch delay from 8 to 4 seconds in TrainerBridge and exported native, Snap, and Flatpak scripts.
- Repairs all Open Folder actions, including Open Backup Folder, by launching the host file manager with a sanitized environment.
- Stores theme and window settings in a stable TrainerBridge INI file and migrates existing Qt settings.
- Uses `Prefix Components - Game` and `Third-Party Notices` as the dialog titles.
- Renames the fallback component category to `Other`.
- Adds a general GE-Proton recommendation after failed component installations without presenting it as a guarantee.
- Adds `Keep Existing Backup & Continue` when a safety backup already exists.
- Strengthens Replace Backup, Delete Backup, and post-restore deletion warnings, including possible loss of local save files and other compatdata-only data.
- Clarifies that copy-on-write backup size is logical size and that file data is initially shared.
- Removes the speculative version 1.0 storage-path promise from Options.
- Preserves the serialized QThread cleanup fix for Restore -> Delete Backup.

- Adds Steam Flatpak support to exported launch scripts using the same sandbox and live-environment detection.
