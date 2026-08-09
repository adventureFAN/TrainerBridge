# Testing TrainerBridge

## Package startup

- [ ] AppImage starts normally.
- [ ] Starting TrainerBridge a second time shows only the already-running notice and does not create a second main window; after the first process exits, a new launch works normally.
- [ ] AppImage starts with `APPIMAGE_EXTRACT_AND_RUN=1`.
- [ ] Portable `.tar.xz` version starts.
- [ ] Icon and About dialog are displayed correctly.
- [ ] System, Light, and Dark themes persist after restart.
- [ ] Open Data, Trainers, Trainer, Game, Prefix, and Backup Folder actions work.
- [ ] Main, Options, About, and Prefix Components window state is restored where supported by the window manager.
- [ ] Live Log shows compact timestamps plus `OK` / `INFO` / `WARNING` / `ERROR` labels, remains useful without polling spam, and records the detailed launch-state transitions.
- [ ] **Copy all**, **Save as...**, and **Clear** work; normal application startup creates no persistent log file.
- [ ] Live Log output shortens the current home directory to `~` (including Bazzite `/home/<user>` and `/var/home/<user>` aliases) before text can be copied or saved.

## Game and trainer launch

- [ ] Launch Game + Trainer works with a native Steam package.
- [ ] Launch Game + Trainer works with Steam Snap.
- [ ] Steam Flatpak permission prompt grants read-only trainer access.
- [ ] Steam Flatpak detects the running AppID session and launches the trainer.
- [ ] Exported native, Snap, and Flatpak scripts launch correctly.
- [ ] Launch Game enables Launch Trainer after verification.
- [ ] Launch Trainer works for an already verified game.
- [ ] Trainer exits normally with code 0.
- [ ] If the game is closed before its TrainerBridge-launched trainer, the trainer closes automatically, no early-exit-components warning is shown for that intentional shutdown, and another game's launch controls become available again.
- [ ] Early non-zero trainer exit shows the runtime-components hint.
- [ ] Publisher-launcher games are not confused with the actual game executable.
- [ ] Native/Snap launch-process matching requires the exact `/proc` argument `AppId=<ID>`; a shorter AppID must not match a longer one (for example `123` must not match `1234`).
- [ ] Exported native/Snap scripts do not treat `SteamLaunch AppId=<ID>` alone as proof that the game is running; they must verify the expected descendant Windows game executable and keep the same game PID stable before the four-second trainer delay.
- [ ] Closing TrainerBridge during game detection cancels the pending launch sequence, leaves the game running, and exits cleanly without a QThread shutdown warning/crash.
- [ ] Closing TrainerBridge during the four-second trainer delay behaves the same way and exits cleanly.

## Prefix Components

- [ ] Native or Flatpak Protontricks is detected without blocking the GUI thread.
- [ ] A deliberately hung Flatpak discovery command times out and reports an error while the Prefix Components dialog remains responsive.
- [ ] Read-only Protontricks catalog/version/status queries are bounded; component installation and Windows-version mutation remain intentionally unbounded.
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

## Focused 1.0.1 regression commands

The build-tool regression also guards the release-container environment banner against `SIGPIPE`/exit 141 under `set -o pipefail`; do not reintroduce an early-closing `ldd --version | head -n 1` pipeline.

Run from the project root with the normal virtual environment active:

```bash
python tests/test_process_monitor_appid.py
python tests/test_exporter_game_detection.py
python tests/test_protontricks_timeouts.py
python tests/test_single_instance.py
python tests/test_version_metadata.py
python tests/test_source_hygiene.py
python tests/test_build_tool_pinning.py
python tests/test_live_log.py
python tests/test_fixed_window_sizes.py
python tests/test_security_boundaries.py
python tests/test_session_lifecycle.py
```

Expected result for the 1.0.1 release candidate: the AppID suite ends with `Ran 5 tests` / `OK`, the exporter suite ends with `Ran 6 tests` / `OK`, the Protontricks timeout/threading suite ends with `Ran 8 tests` / `OK`, the single-instance suite ends with `Ran 7 tests` / `OK`, the version-metadata suite ends with `Ran 8 tests` / `OK`, the source-hygiene suite ends with `Ran 7 tests` / `OK`, the build-tool pinning/build-shell suite ends with `Ran 7 tests` / `OK`, the Live Log suite ends with `Ran 13 tests` / `OK`, the fixed-window suite ends with `Ran 9 tests` / `OK`, and the security-boundary suite ends with `Ran 15 tests` / `OK`, and the game/trainer lifecycle suite ends with `Ran 10 tests` / `OK`.


## Steam manifest and exported-script security boundaries

Run `python tests/test_security_boundaries.py`. The suite verifies that Steam AppIDs contain ASCII digits only before they reach path-sensitive operations, malformed manifest AppIDs are skipped, unsafe `installdir` values cannot escape `steamapps/common`, trainer import/removal and backup setup reject traversal AppIDs, and exported native/Flatpak scripts cannot execute a game name that contains a newline followed by shell syntax.

For a real-host smoke test after this focused suite passes, rescan the normal Steam library, confirm ordinary numeric-AppID games still appear, open one normal Game Folder, and export one configured game script. No deliberately malicious manifest is required on the real machine.


## Public-source privacy

Run `python tests/test_source_hygiene.py`. The suite rejects one-off before-step snapshots and developer-specific identity/path text. It also verifies that the release build checks staged **text** content for absolute Linux home paths without treating upstream paths embedded in third-party binary libraries as developer leaks.


## Fixed window sizes

Run `python tests/test_fixed_window_sizes.py`, then verify on a real desktop that the main window, Prefix Components, Options, About and Third-Party Notices cannot be drag-resized. Toggle the Live Log and confirm the main window switches between its two intended fixed heights without becoming resizable.


## Game-first shutdown lifecycle

Run `python tests/test_session_lifecycle.py`. The suite verifies that trainer launches use a dedicated Unix session/process group, shutdown requests target the whole trainer group rather than only the Proton wrapper, a force-stop fallback exists after the three-second grace period, and an intentional game-exit shutdown cannot be misreported as an early trainer failure.

Real-host regression: use **Launch Game + Trainer**, wait until both are running, then close the **game first while leaving the trainer open**. Within a few seconds the TrainerBridge-launched trainer must close automatically, the Live Log must report the verified game exit followed by trainer shutdown, and selecting a different configured game must make its launch controls available without restarting TrainerBridge.
