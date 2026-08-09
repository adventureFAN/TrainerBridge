# TrainerBridge - Living HANDOFF

**Purpose:** Continuity document for future ChatGPT conversations and later TrainerBridge development.
**Last updated:** 2026-08-09
**Current public stable release:** **TrainerBridge 1.0.1**
**Current source/release candidate:** **TrainerBridge 1.0.1**
**Repository:** https://github.com/adventureFAN/TrainerBridge
**License:** MIT

> This document is intentionally more detailed than a normal README. It records implementation decisions, tested behavior, past traps, and working agreements so a new development chat does not have to reconstruct the project from scratch.

---

## 1. Project in one paragraph

TrainerBridge is a Linux desktop application for launching standalone Windows trainer executables alongside Steam games running through Proton.

It scans Steam libraries, associates games with their Steam AppID, detects each game's compatdata prefix and the actual Proton version selected by Steam, stores one imported trainer per game, launches the game, verifies that the correct Proton session is really running, waits four seconds, and then starts the trainer inside the matching Proton environment.

TrainerBridge does **not** ship trainers, download trainers, modify game files, or bypass anti-cheat systems.

---

## 2. Current release state

TrainerBridge **1.0.0 is publicly released on GitHub**.

Release artifacts:

- `TrainerBridge-1.0.0-x86_64.AppImage`
- `TrainerBridge-1.0.0-x86_64.AppImage.sha256`
- `TrainerBridge-1.0.0-x86_64.tar.xz`
- `TrainerBridge-1.0.0-x86_64.tar.xz.sha256`

Git state at the 1.0 release:

- Main branch: `main`
- Stable tag: `v1.0.0`
- Stable release commit was originally:
  `654ed4d6da8766b1f1a63e12645f9f1c79370122`
- A small CI-only commit was pushed afterward to fix the pip cache dependency path.
- GitHub Actions CI is now **green**.

### CI

`.github/workflows/ci.yml` runs on Ubuntu 22.04 and:

1. checks out the source,
2. installs Python 3.10,
3. caches pip using `requirements-build.txt`,
4. installs Qt/Linux runtime libraries,
5. installs Python dependencies,
6. compiles Python sources,
7. runs `python main.py --self-test` with `QT_QPA_PLATFORM=offscreen`.

Important CI line:

```yaml
cache-dependency-path: requirements-build.txt
```

Without that line `actions/setup-python` looked for `requirements.txt` / `pyproject.toml` and failed.

### Post-release maintenance

A post-release static review of the 1.0.0 source identified several maintenance items for the **1.0.1** patch release. All eight original review findings plus the Live Log, privacy-cleanup, fixed-window UX follow-ups, final security hardening, and the game-first trainer lifecycle fix have been implemented and verified on Bazzite. During the final 1.0.1 package build, the generic release privacy gate then produced a false positive on harmless Qt upstream build paths embedded in vendor ELF binaries (`/home/<vendor-user>/work/...`). The gate has been narrowed to staged text content while public-source hygiene remains strict. The corrected final 1.0.1 package build then completed successfully; both SHA-256 files verified `OK`, and the final AppImage self-test passed with `TrainerBridge 1.0.1`. Publication to GitHub is the remaining release action.

Completed maintenance step 1 — active launch `QThread` shutdown:

- The main-window close path now requests the existing cooperative launch cancellation, ignores the first close event while the worker exits, and automatically closes the window only after the launch thread has finished.
- Real Bazzite runtime proof passed on 2026-08-08 while the launch worker was in the four-second trainer-delay phase: closing TrainerBridge logged both `Cancelling the automatic launch sequence` and `Launch cancelled`, returned normally to the shell with no `QThread: Destroyed while thread is still running` warning, left the game running, and did not start the trainer. Treat this fix as verified; keep it in later launch/shutdown regression testing.

Completed maintenance step 2 — exact native/Snap AppID matching:

- The 1.0.0 `ProcessMonitor._is_real_launch_process()` check could falsely match a shorter AppID inside a longer one, e.g. requested `123` matching `AppId=1234`. The fix now requires the exact null-separated `/proc/<pid>/cmdline` argument `AppId=<ID>` from the parsed argument list.
- Focused regression coverage passed **5/5** on Bazzite, including exact-match acceptance, longer-AppID rejection, embedded-text rejection, and preservation of the `Install=1` / `iscriptevaluator.exe` filters.
- Real Bazzite runtime proof also passed with native Steam and FINAL FANTASY (AppID `1173770`): the actual `FINAL FANTASY.exe` process was detected and the trainer started normally. Treat this fix as verified.

Completed maintenance step 3 — exported native/Snap game-process verification:

- In 1.0.0 the standard exported script considered the Steam `SteamLaunch AppId=<ID>` launcher process sufficient. That could start the trainer even when the expected Windows game executable had not actually appeared or had failed during startup.
- The fixed standard exporter embeds a small standalone Python 3 detector. It mirrors the GUI's important `/proc` checks: exact AppID argument, launch-process filtering, extraction of the expected Windows executable, descendant traversal, Wine preloader verification, first-Windows-EXE matching, and stability of the same game PID for five seconds.
- A mere matching Steam launch process is deliberately **not** enough anymore. The exported script waits up to 60 seconds for the actual game executable, then preserves the normal four-second trainer delay.
- The generated script requires a host `python3` command. Supported Bazzite/Fedora/Ubuntu-family test systems already provide Python 3; keep the explicit readable error if it is absent.
- Focused synthetic `/proc` regression coverage passed **6/6**: launch-process-only rejection, actual-game acceptance, helper-Wine rejection, exact-AppID preservation, stable-PID waiting, and generated Bash syntax/structure. The new test fails against the pre-step-3 exporter because that actual-game detector does not exist there.
- Real Bazzite positive proof passed on 2026-08-08 with the exported native FINAL FANTASY script: it waited for and detected `FINAL FANTASY.exe`, reported the real PID, preserved the four-second delay, and started the trainer successfully.
- A deliberate real-host negative test then sabotaged only the test copy's game-EXE acceptance and shortened its timeout to eight seconds. Steam launched FINAL FANTASY, the exported script timed out with `FINAL FANTASY was not detected within 8 seconds`, and the trainer did **not** start. Treat step 3 as verified. Steam Snap shares this standard exporter path and remains part of the later package/regression matrix.

Completed maintenance step 4 — bounded Protontricks discovery/read-only queries:

- In 1.0.0 `ProtontricksManager.detect()` ran synchronously in the `ComponentsDialog` constructor. For Flatpak Protontricks this could execute `flatpak info com.github.Matoking.protontricks` directly on the GUI thread with no timeout, so a hung Flatpak command could freeze the Prefix Components window.
- Protontricks detection now runs in a dedicated `QThread` worker. The Flatpak presence check is additionally bounded to five seconds so the worker itself cannot remain stuck indefinitely. A timeout is reported as a clear Protontricks detection error rather than misreported as `not installed`.
- Read-only Protontricks calls used to load the Prefix Components catalog (`--version`, `list-installed`, and category `list`) now use a finite 30-second timeout. These commands run in the catalog worker thread, so the GUI remains responsive and a broken Protontricks/Wine/runtime query eventually returns a readable error instead of leaving the dialog busy forever.
- **Do not apply this timeout to prefix-changing operations.** Component installation and Windows-version changes/restoration intentionally remain unbounded because killing Protontricks midway through a prefix mutation could leave the prefix in an uncertain state.
- Focused regression coverage passed **8/8** on Bazzite. Normal Prefix Components loading with the real system Protontricks also passed.
- Two deliberate real-host hang simulations passed: a fake Flatpak `info` call slept for 30 seconds but was stopped after the five-second detection boundary while the dialog remained responsive; a fake system Protontricks `--version` call slept for 40 seconds but was stopped after the 30-second read-only boundary while the dialog remained responsive. Both surfaced readable errors with no Python exception or QThread warning. Treat step 4 as verified.

Completed maintenance step 5 — single-instance protection:

- 1.0.0 allows two independent TrainerBridge processes to run simultaneously. This is more than a cosmetic duplicate-window issue because constructing a `BackupManager` performs interrupted-operation recovery and removes directories named like `.creating-*` and `.trainerbridge-restore-*`. A second process could therefore mistake the first process's live transaction directory for abandoned recovery state.
- 1.0.1 adds one per-user advisory `flock` at `~/.local/share/TrainerBridge/.trainerbridge.lock`. The first process keeps the file descriptor open for its entire normal GUI lifetime. The lock is acquired before logging and before `MainWindow()` can be constructed, so a rejected second process cannot reach Prefix Components or backup recovery.
- The lock file itself may remain on disk, but lock ownership is kernel state rather than file existence. Normal exit releases it explicitly; a crash/SIGKILL/process death releases it automatically. A stale file therefore does not permanently block future launches.
- A rejected second launch displays a small `TrainerBridge is already running` information dialog and exits without constructing the main window. No attempt is made in 1.0.1 to implement inter-process window focusing/activation; the safety goal is serialization.
- Focused regression coverage passed **7/7** on Bazzite. Real source-tree proof also passed: while one instance was running, a second launch showed only the already-running dialog and created no second main window; after the first process was deliberately terminated with `SIGKILL`, TrainerBridge started normally again immediately with no stale-lock refusal. Treat step 5 as verified.

Completed maintenance step 6 — single-source runtime/build version metadata:

- In 1.0.0 the semantic version existed independently as `APP_VERSION = "1.0.0"`, `APP_DISPLAY_VERSION = "1.0"`, and `X-AppImage-Version=1.0.0` in the desktop file. A patch release could therefore easily ship mismatched About/Qt/AppImage metadata.
- The fixed tree keeps only `APP_VERSION` in `core/version.py` as runtime/build version authority. About, Qt application metadata and self-test output use `APP_VERSION` directly.
- Release artifact filenames already derive from `APP_VERSION`; the AppImage build now injects that same value into the staged desktop file as `X-AppImage-Version` instead of keeping a second hard-coded copy in the source desktop file.
- Historical release notes, old artifact examples and changelog entries are intentionally not rewritten by this refactor; they describe the actual 1.0.0 release and are not runtime/build version authorities.
- Living installation/build/troubleshooting examples now use a `<version>` placeholder, and the bug-report template no longer pins `1.0.0`, so those maintained files do not become stale merely because a patch release changes the version. Version-specific release notes/checklists/changelog history remain explicit by design.
- Focused version-metadata regression coverage passed **8/8** on Bazzite. The source-tree self-test also reported `TrainerBridge 1.0.0`, and the visible About dialog now reports the same full `Version 1.0.0` instead of the separate shortened `1.0` display value. Treat step 6 as verified.
- Keep the source version at the currently released value until the final 1.0.1 release bump. Once all maintenance/UX work is verified, changing the single `APP_VERSION` line to `1.0.1` must update About/Qt/build filenames/AppImage metadata together.

Completed maintenance step 7 — source-tree cleanup:

- The obsolete root-level `APPLY_NOTES.md` and `FLATPAK_RUNTIME_FIX_NOTES.md` were removed. They were one-off development/repair notes from the 1.0 RC cycle and were not referenced by runtime/build code. Historical release documentation under `docs/` remains untouched.
- The accidental duplicate consecutive `@Slot(object)` decorator on `ComponentsDialog._components_loaded` was reduced to exactly one object slot without changing the method's behavior.
- Focused source-hygiene regression coverage passed **4/4** on Bazzite, and a real Prefix Components GUI smoke test loaded the catalog, remained responsive and closed normally with no exception or freeze. Treat step 7 as verified.

Completed maintenance step 8 — deterministic `appimagetool` source + pipefail-safe build probe:

- The 1.0.0 build downloaded `appimagetool` from the legacy `AppImage/AppImageKit` repository's floating `continuous` release. Upstream now marks that AppImageKit build path obsolete and directs users to the maintained `AppImage/appimagetool` repository.
- The build is pinned to upstream `appimagetool` **1.9.1** from `AppImage/appimagetool/releases/download/1.9.1/...` instead of `continuous`.
- The local cached filename includes the pinned version (`appimagetool-1.9.1-x86_64.AppImage`). This prevents a machine that built 1.0.0 from silently reusing the old floating `appimagetool-x86_64.AppImage`.
- The first real Bazzite release-container run exposed a separate pre-existing shell bug before PyInstaller started: `ldd --version | head -n 1` under `set -euo pipefail` can make `ldd` receive SIGPIPE and return 141. A dedicated 500-iteration probe reproduced exit 141 immediately. The banner now uses `ldd --version 2>&1 | sed -n '1p'`, and the regression test exercises this form with a deliberately verbose fake `ldd`.
- Focused build-tool coverage passed **7/7** on Bazzite. The corrected Ubuntu 22.04 Podman build then completed, generated AppImage + SHA-256 sidecar + portable tar.xz + SHA-256 sidecar, both checksums verified, the AppImage self-test passed, and a real GUI smoke test passed. Treat step 8 as verified.

Completed 1.0.1 UX step 9 — PIA-style in-app Live Log:

- The Live Log is being changed to compact `HH:MM:SS` timestamps plus explicit `OK`, `INFO`, `WARNING`, and `ERROR` labels for meaningful events.
- Launch progress crosses the existing launch-worker thread boundary through a dedicated Qt signal. The session manager reports only useful state changes: already-running check, Steam launch, waiting for the real game executable to remain stable for five seconds, verified executable/PID, the four-second trainer delay, trainer start, cancellation and failures. Do **not** add per-poll spam.
- Normal application startup must create **no persistent log file** and must not redirect stdout/stderr into a disk logger. Low-level terminal `print` diagnostics may remain visible when TrainerBridge is started from a terminal.
- The Live Log panel provides **Copy all**, **Save as...**, and **Clear**. `Save as...` writes plain text only to the exact path selected by the user. There is no `Save Live Log` preference.
- Before display, the current user home is shortened to `~`; on Bazzite both `/home/<user>` and `/var/home/<user>` forms are treated as the same private home path. Because Copy/Save operate on the visible text, manually shared logs inherit that privacy normalization.
- The old About-dialog **Open Log Folder** action and active documentation that tells users to fetch automatic logs from `~/.local/share/TrainerBridge/logs/` are removed. Existing legacy log files from older builds are not automatically deleted.
- Real-host verification completed for normal game+trainer launch, Copy/Save/Clear, absence of automatic log files, controlled timeout `ERROR`, cooperative-cancel `WARNING` output, and visual confirmation that Bazzite `/home/<user>` / `/var/home/<user>` paths are shortened to `~`. Treat step 9 as verified.

Completed maintenance step 10 — public-source privacy cleanup:

- Removed one-off `*.before-step*` development snapshots from the source tree and ignored future files with that pattern.
- Live-log privacy tests use neutral fixture usernames rather than developer-specific names.
- The release build no longer checks for one hard-coded developer path; it rejects any embedded absolute `/home/<user>/...` or `/var/home/<user>/...` path in the staged AppDir, while still rejecting the historical `ProtonTrainerManager` name.
- Source-hygiene regression coverage checks that no one-off snapshots, developer identifier, or concrete absolute home path remains in public source text. `adventureFAN` remains intentionally public as the project-owner/GitHub identity.

Completed 1.0.1 UX step 11 — fixed TrainerBridge window sizes:

- Every TrainerBridge-owned custom top-level window/dialog is now non-resizable. Native system file dialogs and standard message boxes are not forced to a custom size.
- Main window: fixed `1220x800` while the Live Log is visible and fixed `1220x620` while it is hidden. Toggling the Live Log immediately switches between those two defined sizes.
- Prefix Components: fixed `1000x700`. Options: fixed `620x460`. About: fixed `520x500`. Third-Party Notices: fixed `720x560`.
- Saved geometry may still restore window position, main-window state and splitter layout, but it cannot override the defined fixed size. The Options wording therefore says **Remember window positions and layout** instead of claiming arbitrary window sizes are remembered.
- Focused regression coverage passed **9/9**, and real Bazzite visual/drag-resize smoke testing confirmed the intended fixed sizes and Live-Log height switch. Treat step 11 as verified.


Completed maintenance step 12 — Steam manifest/path validation and exported-script comment hardening:

- A final independent review found that `appid` was read from `appmanifest_*.acf` and then used as a path component in trainer storage and backup/recovery paths without a central format check. Because `pathlib` discards the left side of `/` for an absolute right-hand operand and honors `..`, a crafted manifest AppID could make path-sensitive code leave TrainerBridge's intended data tree. A local pre-fix reproduction confirmed that `storage.import_trainer("../escaped", ...)` wrote outside the trainer root.
- `core.validation.validate_steam_appid()` now accepts only one or more ASCII digits and normalizes accepted values to `str`. The scanner validates before constructing compatdata paths; `GameProfile` maintains the same invariant; destructive trainer-storage and backup-manager boundaries validate again as defense in depth. Steam URI construction, exporter generation and Protontricks prefix lookup also reject invalid AppIDs before using them.
- Steam manifest `installdir` is treated as one relative directory name. Absolute, nested/traversal, empty and NUL-containing values do not become a `steamapps/common/...` path. A game with a valid AppID but unsafe `installdir` may still appear and launch, but its Game Folder action is disabled (`game_path=None`).
- The same review found that both exported Bash variants interpolated `game.name` directly into a comment. A newline in the name could terminate that comment and turn following text into shell code even though `GAME_NAME` itself was correctly `shlex.quote()`-escaped. A pre-fix local reproduction executed the injected command. Exported headers are now generic (`# Exported by TrainerBridge.`); the game name appears only in the quoted shell variable.
- Focused security-boundary coverage adds **15 tests** for valid/invalid AppIDs, scanner behavior, `installdir` containment, trainer import/removal traversal, backup setup, secondary launch/prefix boundaries, both exporter variants, and a real Bash execution probe proving that newline-containing game names remain inert. The complete source-level 1.0.1 suite is **85/85** locally after this patch. Real Bazzite smoke/build verification is still required before publication.
- Two lower-priority review notes were deliberately not changed in this patch: compressed restore still preserves Proton/Wine absolute symlinks and uses per-member destination checks plus hardlink rejection; changing symlink semantics immediately before release risks breaking valid prefixes. Data-directory permissions continue to follow the user's normal home/umask policy. Revisit either only with dedicated compatibility/security tests rather than a last-minute speculative change.

Completed maintenance step 13 — game-first trainer-session cleanup:

- The final Bazzite smoke test found a real ordering bug that earlier testing had accidentally hidden: when the user closed the game first but left the TrainerBridge-launched trainer running, `Verified game <appid> exited` was logged but the trainer process remained alive. Because the UI deliberately treats a running TrainerBridge trainer as a global busy session, launch controls for other games stayed disabled until the old trainer was manually closed. Earlier tests happened to close the trainer first, so the state was always released normally.
- Trainer launches now use `start_new_session=True`, giving the Proton trainer wrapper and its descendants a dedicated Unix process group separate from TrainerBridge. Session state records that process-group ID. This is important because stopping only the outer Proton wrapper can otherwise leave the actual Wine trainer process behind.
- When the verified game exits while its TrainerBridge-launched trainer is still alive, the GUI sends a non-blocking SIGTERM to the trainer process group, keeps the session busy while shutdown is in progress, and automatically escalates to SIGKILL after a three-second grace period if the trainer group is stubborn. Once the group is gone, `active_session` is cleared and other games can be launched immediately without restarting TrainerBridge.
- This automatic stop is intentional lifecycle cleanup, not a trainer crash. It therefore logs `Trainer for <game> stopped because the game exited` and does not show the early non-zero-exit Prefix Components warning. Existing behavior when the trainer exits first remains unchanged.
- The launch-worker cancellation cleanup path uses the same process-group-aware stop helper, but may wait because it already runs off the GUI thread. The normal GUI game-exit path remains non-blocking.
- Focused lifecycle coverage adds **10 tests**, including a real local subprocess-group termination probe. Together with the previous suites, the complete source-level 1.0.1 regression set is **95/95** locally.
- Real Bazzite regression proof passed on 2026-08-09: after **Launch Game + Trainer**, closing FINAL FANTASY first automatically stopped the still-running trainer and released the session; another game could then be launched without restarting TrainerBridge. Treat this lifecycle fix as verified.

Completed maintenance step 14 — release privacy-gate binary false positive:

- The first final 1.0.1 package build passed the frozen and AppDir self-tests but stopped before AppImage creation because the generic staged-path scan used `grep -a` over every file in the AppDir. Qt's vendor ELF libraries legitimately contain their own upstream source paths such as `/home/<vendor-user>/work/qt/...`, so they were incorrectly classified as TrainerBridge developer-path leaks.
- The release gate now scans staged **text** content (`grep -I`) for `/home/<user>/...` and `/var/home/<user>/...` paths. Third-party binaries are intentionally ignored by this particular privacy check; they are still covered by normal packaging/self-tests and the GLIBC scan.
- TrainerBridge-owned public source remains separately strict: `tests/test_source_hygiene.py` rejects concrete developer identifiers and absolute home paths in source text. This preserves the intended privacy guarantee without pretending that upstream vendor binaries were built without upstream build paths.
- Focused regression coverage explicitly checks that the build script uses the binary-ignoring text scan and does not regress to the old `grep -a` behavior. The corrected final package build passed on Bazzite; both release checksums verified `OK`, and the freshly built AppImage self-test passed with application metadata `TrainerBridge 1.0.1`. Treat the packaging/privacy correction as verified.

Completed release-preparation step 15 — GitHub publication handoff:

- `docs/RELEASE_NOTES_1.0.1.md` contains the curated GitHub release notes for 1.0.1.
- `docs/GITHUB_RELEASE_CHECKLIST.md` now documents the 1.0.1 publication flow instead of the old 1.0.0 first-release procedure.
- `scripts/publish_github_release.sh` performs the final source/release handoff: it verifies the current version, repository/branch, GitHub CLI authentication, release checksums, final AppImage self-test, source hygiene and version metadata; stages the public source; rejects generated/local paths; shows the staged source before confirmation; commits/pushes `main`; creates/pushes annotated tag `v1.0.1`; and uploads the four final binaries/checksums to a **draft** GitHub Release.
- The helper deliberately leaves the GitHub Release as a draft for one final human review before clicking **Publish release**. GitHub-provided source ZIP/tar.gz archives come from the tagged commit, so no separate manually built source archive is required for the public release.
- GitHub commit-email privacy is part of the release procedure. During the 1.0.1 publication, the first `git push origin main` was rejected with `GH007: Your push would publish a private email address` even though `gh auth status` was healthy. Keep GitHub's private-email protection enabled; do **not** disable it as a workaround. For this repository, configure the Git identity locally with `git config --local user.name <github-login>` and the GitHub noreply address `<github-id>+<github-login>@users.noreply.github.com`. The numeric ID/login can be obtained with `gh api user --jq '.id'` and `gh api user --jq '.login'`. If the offending commit has not been pushed yet, rewrite only that local commit with `git commit --amend --reset-author --no-edit`, verify Author/Committer, then push again. The corrected 1.0.1 source push succeeded with this procedure. Prefer repository-local Git identity over changing the user's global Git configuration.

### Source of truth

For future development, the **GitHub `main` branch / a fresh archive made from the local current checkout is the source of truth**.

Do not reconstruct a future patch from old ZIPs in previous chats. Several old archives predate later Flatpak, theme, release, or CI fixes.

---

## 3. Development working agreement

The project owner is **adventureFAN**. TrainerBridge was developed collaboratively with ChatGPT by OpenAI; the About dialog credits:

`adventureFAN & ChatGPT`

For future work:

- Treat TrainerBridge 1.0.0 as the stable baseline for understanding regressions; 1.0.1 is the current maintenance release candidate.
- Do not make speculative changes to working code just because something seems theoretically cleaner.
- Before a substantial code change, inspect the **current complete project archive/source tree**.
- Prefer complete replacement files or a small ZIP patch over asking the user to manually edit Python.
- Treat the project owner as a development beginner for all hands-on instructions. Give copy/paste-ready commands, explicit paths, explain what step is being performed, and state the exact PASS/output or visible behavior to expect. Do not assume that virtual-environment activation, project launch commands, Git/build tooling, or prior terminal steps are remembered. Prefer one small action at a time and do not ask the user to hand-edit code unless necessary.
- For source-tree GUI tests, explicitly remind the user of the normal launch sequence when needed: `cd ~/TrainerBridge`, `source venv/bin/activate`, then `python main.py`.
- After 1.0, changes should be driven by real bugs or clearly useful features found during actual use.
- Preserve working support for native Steam, Steam Snap, and Steam Flatpak.
- Never sacrifice an already-tested path while fixing a different packaging variant.
- Safety around Proton prefixes and backups is more important than convenience.
- Test conservatively: prefer one targeted test too many over one too few. Small regression tests have already exposed serious bugs in this project, so do not skip a narrow test just because a change looks simple.

---

## 4. Project paths and persistent data

Typical development checkout:

```text
~/TrainerBridge
```

Application data:

```text
~/.local/share/TrainerBridge/
```

Important persistent paths:

```text
~/.local/share/TrainerBridge/trainers/<AppID>/
~/.local/share/TrainerBridge/backups/
~/.local/share/TrainerBridge/trainers.json
~/.local/share/TrainerBridge/settings.ini
```

Imported trainers are copied into TrainerBridge's own data directory instead of being referenced from arbitrary download locations.

---

## 5. Important source files

Top-level GUI:

- `main.py` - main window, menus, actions, game list, launch controls, live log.
- `components_dialog.py` - Prefix Components UI and backup/restore UI.
- `options_dialog.py` - application settings.
- `about_dialog.py` - About / credits / project information.

Core:

- `core/scanner.py` - complete game scan.
- `core/steam.py` - Steam installation and library discovery.
- `core/games.py` - game discovery.
- `core/proton.py` - Proton detection from prefix `config_info`.
- `core/models.py` - `GameProfile`.
- `core/process_monitor.py` - game-session verification and `GameRuntime`.
- `core/session_manager.py` - launch orchestration and cancellation.
- `core/game_launcher.py` - launches Steam games.
- `core/trainer_launcher.py` - launches trainer in the correct Proton context.
- `core/flatpak_steam.py` - Steam Flatpak detection, permission handling, sandbox/session probing, trainer launch.
- `core/exporter.py` - standalone exported launch scripts.
- `core/protontricks.py` - Protontricks discovery/catalog/install/state handling.
- `core/backup_manager.py` - safety backup, verification, restore, delete.
- `core/preferences.py` - shared settings, themes, geometry.
- `core/desktop.py` - folder/URL opening with sanitized host environment.
- `core/host_process.py` - removes PyInstaller/Qt environment contamination before host commands.
- `core/storage.py` - trainer configuration persistence.
- `core/paths.py` - data/cache/log/trainer/backup locations.
- `core/version.py` - version and project metadata.

Build/release:

- `scripts/build_appimage.sh`
- `scripts/build_inside_container.sh`
- `scripts/collect_licenses.py`
- `packaging/container/Dockerfile`
- `packaging/AppRun`
- `packaging/TrainerBridge.spec`

Documentation:

- `README.md`
- `CHANGELOG.md`
- `docs/BUILDING.md`
- `docs/TESTING.md`
- `docs/TROUBLESHOOTING.md`
- `docs/GITHUB_RELEASE_CHECKLIST.md`
- `SECURITY.md`
- `CONTRIBUTING.md`

---

## 6. Main launch workflow

Normal `Launch Game + Trainer` behavior:

1. User selects a configured Steam game.
2. TrainerBridge launches the game through the detected Steam installation.
3. It waits up to **60 seconds** for the correct Proton session.
4. It verifies the real game session instead of treating any Wine helper as the game.
5. Session must be stable before TrainerBridge proceeds.
6. TrainerBridge waits an additional **4 seconds**.
7. Trainer is started with the exact Proton/prefix context.
8. User can cancel the pending trainer sequence while leaving the game running.

Important historical fix:

- `iscriptevaluator.exe` and similar helper processes must not be mistaken for the real game.
- Trainer launch uses Proton's `runinprefix`, not a naïve `proton run`, because the latter previously caused bad lifecycle/shutdown behavior.
- Exported scripts use the same 60-second session timeout and four-second trainer delay.

---

## 7. Steam package support

### Native Steam

Standard Linux package installations are supported.

TrainerBridge scans normal Steam roots and all configured `libraryfolders.vdf` libraries.

### Steam Snap

Ubuntu Steam Snap support was added and manually tested.

Important Snap root:

```text
~/snap/steam/common/.local/share/Steam
```

Games must be launched through Snap (`snap run steam` path/handling) rather than assuming a native Steam binary.

Do not regress Snap-specific Steam root and launch handling.

### Steam Flatpak

Steam Flatpak was the hardest integration and is fully working in 1.0.

Steam Flatpak root:

```text
~/.var/app/com.valvesoftware.Steam/.local/share/Steam
```

Flatpak application ID:

```text
com.valvesoftware.Steam
```

#### Permission requirement

Steam Flatpak cannot normally see:

```text
~/.local/share/TrainerBridge/trainers
```

TrainerBridge detects this and can grant **read-only** access to that folder. Steam Flatpak must be completely restarted after the permission change.

Do not move or duplicate trainers into Steam's data directory as a workaround. The design intentionally keeps TrainerBridge's normal trainer folder as the single source.

#### Flatpak game detection

Do not rely only on host `/proc` topology.

Each running game can create its own nested Flatpak/Pressure Vessel instance.

The working approach:

1. list running Steam Flatpak instances;
2. find the game-specific instance;
3. inspect the sandbox;
4. find a process associated with the expected AppID, especially the Steam `reaper` process containing:
   `SteamLaunch AppId=<AppID>`;
5. validate `SteamAppId` / `STEAM_COMPAT_APP_ID`;
6. use the live game's Steam environment.

Example validated values during testing:

```text
SteamAppId=1173770
SteamGameId=1173770
STEAM_COMPAT_APP_ID=1173770
STEAM_COMPAT_DATA_PATH=.../steamapps/compatdata/1173770
```

#### Flatpak trainer launch

A plain `flatpak enter ... proton runinprefix trainer.exe` was **not enough** even though it exited with code 0.

The trainer only became visible when TrainerBridge copied the **live environment from the running Steam game process**, including desktop/session values such as:

```text
HOME
DISPLAY
XDG_RUNTIME_DIR
DBUS_SESSION_BUS_ADDRESS
SteamAppId
STEAM_COMPAT_APP_ID
STEAM_COMPAT_DATA_PATH
```

The trainer is then started inside the running game sandbox with the detected Proton `runinprefix`.

This is essential. Do not simplify it back to a basic `flatpak enter`.

Exported launch scripts also support this Flatpak mechanism and were manually tested successfully.

---

## 8. Proton detection

The correct Proton version is detected from the game's prefix `config_info`.

Past issue:

The stored path may point somewhere inside a Proton installation rather than directly at its root.

Current logic walks upward and accepts a Proton root only when the candidate contains a direct executable:

```text
<root>/proton
```

This was tested with multiple official Proton releases and GE-Proton.

Do not infer Proton from a hard-coded version table.

---

## 9. Prefix Components / Protontricks

Prefix Components is an optional Protontricks frontend.

It supports:

- native Protontricks,
- Flatpak Protontricks,
- searchable component catalog,
- categories,
- multi-select,
- installed-state display,
- installed-only filtering,
- refresh,
- Windows-version protection/restoration,
- `--no-bwrap` fallback when needed.

Window title:

```text
Prefix Components - <Game>
```

Fallback category label:

```text
Other
```

### Important Flatpak Protontricks limitation

Commands equivalent to custom shell execution such as:

```text
protontricks -c "winecfg /v"
reg query ...
```

were unreliable/not available in Flatpak Protontricks.

TrainerBridge therefore reads relevant Wine registry information directly from the prefix (`user.reg`) rather than depending on unsupported custom shell commands.

Keep this design unless there is a proven better cross-package method.

### Windows-version protection

Some Winetricks recipes temporarily change the emulated Windows version (for example dotnet-related recipes).

TrainerBridge records/protects/restores the prefix Windows version so a component install does not silently leave a game at an unintended setting such as Windows 7.

### Failed component installations

After a component installation failure, TrainerBridge gives a **general GE-Proton recommendation**, because GE-Proton was the most reliable tested option.

This is deliberately only a recommendation, not a guarantee.

Meaning:

- Compatibility depends on Proton/Wine version,
- current prefix state,
- component,
- Winetricks recipe.

### `dotnet30`

A failure such as:

```text
dotnet30 does not work on a 64-bit installation
WINEARCH=win32 required
```

is a genuine component/prefix architecture incompatibility, not a GE-Proton bug.

### Unresolved prefix-version investigation

There was evidence that an old/modified Proton prefix could behave badly after switching Proton versions, especially after previous failed runtime/component installations.

A freshly recreated prefix later installed `dotnet40/48` successfully.

However, this was **not investigated far enough to justify automatic warnings or destructive behavior**.

Future work must test this carefully before changing TrainerBridge. Do not assume every component failure is caused by switching Proton versions.

---

## 10. Safety backup system

Prefix Components has a safety-backup system because runtime installation can damage a working Proton prefix.

TrainerBridge backs up the **complete `compatdata/<AppID>` directory**, not just selected registry files.

### One backup per game

There is at most one TrainerBridge safety backup for each game.

Backup policy:

- Ask
- Always
- Never

Backup storage:

- Automatic
- Compressed Archive
- Folder

### Btrfs / Copy-on-Write

On a compatible Btrfs filesystem TrainerBridge can use reflink/copy-on-write folder backups.

Important UX fact:

A CoW backup can appear to have the **same logical size as the source**, even though many blocks are shared and the additional physical disk usage is much lower.

Do not treat identical logical size as evidence that CoW failed.

### Compressed backup

Fallback/explicit compressed format:

```text
.tar.zst
```

Restore logic validates the archive and safely handles valid absolute Wine symlinks while blocking unsafe extraction behavior/hard links.

### Existing backup dialog

When a safety backup already exists, the intended choices are:

- `Replace Backup`
- `Keep Existing Backup & Continue`
- `Cancel`

`Keep Existing Backup & Continue` is important: users may want to install another component while preserving a previously tested recovery point.

### Replace warning

Replacing should explicitly explain that the previous tested recovery point will be lost and should normally only be replaced after the current game/trainer configuration was successfully tested.

### Delete warning

Deleting a backup must explicitly warn about irreversible loss, including data that may exist only in the backup:

- local saves,
- game settings,
- registry state,
- installed runtimes,
- DLL overrides,
- other compatdata-only files.

### Restore/Delete lifecycle bug

A previous bug could close the whole Qt application when:

1. backup was restored,
2. user immediately chose to delete it in the success prompt.

Cause: chained QThread lifecycle/cleanup race.

Current solution serializes backup worker cleanup and only begins the next backup operation after the previous QThread object has actually been destroyed.

Do not reintroduce immediate chained backup worker creation before Qt cleanup finishes.

---

## 11. Settings and themes

Themes:

- System
- Light
- Dark

Settings file:

```text
~/.local/share/TrainerBridge/settings.ini
```

A serious pre-1.0 bug caused duplicate `[%General]` sections, for example both:

```ini
theme=system
```

and later:

```ini
theme=dark
```

Different QSettings instances could overwrite each other.

Current implementation:

- uses one shared application settings instance,
- uses:
  `appearance/theme`
- uses:
  `appearance/remember_window_geometry`
- migrates legacy General values,
- persists theme correctly.

Do not recreate separate competing QSettings writers.

TrainerBridge also remembers window geometry/state where the window manager allows it.

---

## 12. Folder opening

Supported folder actions include:

- Open Data Folder
- Open Trainers Folder
- Open Trainer Folder
- Open Game Folder
- Open Prefix Folder
- Open Backup Folder

These previously broke in packaged/AppImage environments.

Current solution uses centralized host opening via `core/desktop.py` and a sanitized host environment from `core/host_process.py`.

Do not call arbitrary `xdg-open` using the raw PyInstaller/AppImage Qt environment because bundled library/plugin variables can break host applications.

---

## 13. Exported launch scripts

TrainerBridge can export standalone launch scripts per configured game.

They support:

- native Steam,
- Steam Snap,
- Steam Flatpak.

Important behavior:

- 60-second detection timeout,
- stable session verification,
- four-second trainer delay,
- correct AppID handling,
- correct Proton/prefix,
- `/proc/*/cmdline` handling without storing NUL bytes in Bash variables,
- Flatpak uses the same live-session/sandbox environment strategy as the GUI.

Export functionality was manually tested successfully with Steam Flatpak before 1.0 release.

---

## 14. UI / UX decisions that are deliberate

Do not casually revert these:

- Main app title: `TrainerBridge`
- Prefix Components title:
  `Prefix Components - <Game>`
- Third-party window title:
  `Third-Party Notices`
- Avoid unnecessary long typographic em/en dashes in window titles.
- Prefix Components fallback category: `Other`
- Trainer delay: **4 seconds**
- Launch detection timeout: **60 seconds**
- Main launch action can become `Cancel Launch` while waiting.
- Canceling the trainer sequence does **not** terminate the already-running game.
- TrainerBridge stores and manages imported trainer executables itself.
- Storage locations are currently fixed; documentation should not promise that configurable storage will arrive in a particular future version.

---

## 15. Error handling philosophy

Do not overdiagnose.

Examples:

- An early trainer exit with code 255 can suggest a missing runtime, but TrainerBridge should not assert exactly which runtime is missing.
- A component failure can suggest trying GE-Proton, but should not claim GE-Proton always works.
- A Wine/Proton trainer that works under Windows is not guaranteed to work on Linux.

Logs should provide technical detail; user-facing dialogs should provide the safest next action without pretending certainty.

---

## 16. Tested configurations for 1.0

Manually tested during development:

Distributions:

- Bazzite
- Fedora Workstation
- Ubuntu
- Linux Mint
- CachyOS

Steam packaging:

- native Steam
- Steam Snap
- Steam Flatpak

Compatibility tools:

- official Proton releases
- GE-Proton

Protontricks:

- native
- Flatpak

This is good coverage for a 1.0 release but not a claim that every Linux distribution, filesystem, desktop, Steam layout, game, trainer, or Proton version is guaranteed.

User explicitly considered this enough for 1.0: remaining bugs should be found through real-world use and bug reports rather than endless distro testing.

---

## 17. Release build

Release builds use an **Ubuntu 22.04 container** to avoid accidentally requiring a host distro's newer glibc.

Supported container engines:

- Podman (preferred on Bazzite/Fedora)
- Docker

Build:

```bash
cd ~/TrainerBridge
./scripts/build_appimage.sh
```

Expected 1.0.1 artifacts:

```text
release/TrainerBridge-1.0.1-x86_64.AppImage
release/TrainerBridge-1.0.1-x86_64.AppImage.sha256
release/TrainerBridge-1.0.1-x86_64.tar.xz
release/TrainerBridge-1.0.1-x86_64.tar.xz.sha256
```

The build performs multiple self-tests and rejects known bad release conditions, including developer-specific absolute home paths in staged text content such as `/home/<user>/...` or `/var/home/<user>/...` and the old project name `ProtonTrainerManager`. Vendor binaries are excluded from the home-path text check because upstream Qt libraries can legitimately contain their own build paths such as `/home/<vendor-user>/work/...`; TrainerBridge-owned source privacy is enforced separately by `tests/test_source_hygiene.py`.

The portable `.tar.xz` is the FUSE-free fallback.

Licenses for bundled Python/Qt dependencies are collected into the release packages.

---

## 18. Release smoke test

Before a future release, at minimum check:

```text
AppImage normal startup
APPIMAGE_EXTRACT_AND_RUN startup
portable archive startup
About/version
System/Light/Dark persistence
window persistence
Open Folder actions
native Steam launch
Snap Steam launch
Flatpak Steam launch + trainer
exported scripts
Prefix Components
backup keep/replace/delete
restore
restore followed immediately by Delete Backup
```

For a small patch, test the changed area plus the most critical launch paths instead of repeating every distro test from scratch.

---

## 19. Public GitHub project

Repository:

```text
https://github.com/adventureFAN/TrainerBridge
```

Project includes:

- README
- MIT LICENSE
- CHANGELOG
- CONTRIBUTING
- SECURITY
- bug report template
- feature request template
- pull request template
- CI workflow
- build/testing/troubleshooting docs
- release assets and SHA-256 files

Users should report bugs through GitHub Issues and include distribution, Steam package type, Proton version, AppID, relevant logs, etc.

Do not ask users to upload trainer binaries, game files, save files, entire prefixes, or personal data.

---

## 20. Distribution / discovery idea after 1.0

Possible future non-code task:

- submit TrainerBridge to the AppImage ecosystem catalog (`AppImage/appimage.github.io` / AppImageHub).

Before doing so, inspect whether the AppImage contains suitable AppStream/metainfo metadata. This was discussed but was **not confirmed as completed** in the original release conversation.

This is distribution/visibility work, not a 1.0 feature requirement.

---

## 21. Historical name

TrainerBridge evolved from the earlier prototype/project idea:

```text
Proton Trainer Manager / ProtonTrainerManager
```

Current public/project name is exclusively:

```text
TrainerBridge
```

Do not revive the old name in UI, docs, release packages, or paths.

---

## 22. Starting a new development chat

Best workflow:

### Step 1 - archive the actual current checkout

From the current project directory:

```bash
cd ~/TrainerBridge

zip -r ~/TrainerBridge-current.zip . \
  -x ".git/*" \
  -x "venv/*" \
  -x ".build-venv/*" \
  -x "release/*" \
  -x "build/*" \
  -x "dist/*" \
  -x "TrainerBridge.AppDir/*" \
  -x "__pycache__/*" \
  -x "*/__pycache__/*" \
  -x "*.pyc" \
  -x "*.AppImage"
```

### Step 2 - upload two files

Upload:

1. `TrainerBridge-current.zip`
2. this HANDOFF file

### Step 3 - tell the new ChatGPT instance

Something as simple as:

```text
We are continuing development of TrainerBridge.
Please read the HANDOFF first, then inspect the complete current source archive before proposing code changes.
```

### Step 4 - do not patch immediately

The new assistant should inspect the actual current source tree and reconcile it with the HANDOFF before generating a patch.

The HANDOFF explains intent/history; the uploaded source is authoritative for exact current code.

---

## 23. Current future-development stance

TrainerBridge 1.0 covers the original vision.

There is currently no requirement to invent features merely to justify a 1.1.

The preferred approach is:

1. use TrainerBridge normally,
2. collect real annoyances/bugs,
3. accept useful GitHub reports,
4. group meaningful improvements into a later release.

Potential future requests from users (Heroic, other launchers, etc.) should be evaluated on actual demand and technical fit, not automatically accepted.

---

## 24. Quick "do not regress" checklist for a future ChatGPT

Before declaring a change finished, ask:

- Did native Steam still work?
- Did Steam Snap still work?
- Did Steam Flatpak's special live-environment path remain intact?
- Did Proton detection still use the game's real selected Proton?
- Did trainer launch still use `runinprefix`?
- If the game exits before its TrainerBridge-launched trainer, does the trainer process group stop and does the session release so another game can be launched?
- Is the 4-second delay preserved unless deliberately changed?
- Does closing TrainerBridge during an active launch cancel cooperatively, leave the game running, and wait for the launch QThread to finish before the window is destroyed?
- Are safety backups still complete compatdata backups?
- Can an existing good backup be kept while installing another component?
- Are Replace/Delete warnings still explicit about savegame/data loss?
- Does Restore -> immediate Delete keep the application alive?
- Does theme persistence still have one authoritative settings writer?
- Do folder actions use the sanitized host environment?
- Do exported scripts still match GUI launch behavior?
- Were old/unsupported assumptions about Protontricks Flatpak avoided?
- Was the current full source inspected before making the patch?

If yes, the change is much less likely to undo one of the hard-won 1.0 fixes.

---

# End of HANDOFF

Update this file whenever a future release changes architecture, support status, important safety behavior, or an implementation decision that a later developer/ChatGPT instance would otherwise have to rediscover.
