# TrainerBridge 1.0 RC1 theme persistence fix

- Uses one shared QSettings instance for every window.
- Moves appearance values away from QSettings' reserved General section.
- Migrates duplicated legacy [%General] sections and keeps the newest value.
- Stops apply_theme() from writing settings during startup or preview.
