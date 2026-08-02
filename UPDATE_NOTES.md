# TrainerBridge launch cancellation and timeout fix

This patch contains:

- `main.py`
- `core/exporter.py`
- `core/process_monitor.py`
- `core/session_manager.py`

Changes:

- Exported launch scripts no longer copy NUL-separated `/proc/*/cmdline`
  data into Bash variables, preventing repeated NUL-byte warnings.
- Exported scripts keep the working Steam launch-process detection.
- Session detection timeout is consistently 60 seconds.
- The main `Launch Game + Trainer` button changes to `Cancel Launch`
  while TrainerBridge is waiting.
- Cancelling stops only TrainerBridge's automatic launch sequence. It does
  not terminate Steam or the game that was already launched.
- Cancellation also works during the additional trainer delay.
- The UI changes to `Cancelling...` after the user requests cancellation.
