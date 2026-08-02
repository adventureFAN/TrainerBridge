# Restore/Delete lifecycle fix

- Waits for the completed backup QThread object to be fully destroyed before processing the result.
- Prevents an immediate Restore -> Delete Backup chain from starting a second worker while the previous Qt thread is still pending deletion.
- Keeps the Prefix Components dialog busy during the short cleanup phase.
- Based on the TrainerBridge 0.99 Beta 1 polish source state.
