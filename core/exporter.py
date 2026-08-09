import shlex
from pathlib import Path

from core.flatpak_steam import _SESSION_PROBE, _TRAINER_LAUNCHER
from core.steam import STEAM_FLATPAK_APP_ID, get_steam_info
from core.validation import validate_steam_appid


SESSION_TIMEOUT_SECONDS = 60
SESSION_STABLE_SECONDS = 5
TRAINER_DELAY_SECONDS = 4


_STANDARD_GAME_DETECTOR = r'''import os
import sys
import time
from pathlib import Path

appid = str(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "once"
timeout = float(sys.argv[3]) if len(sys.argv) > 3 else 60.0
stable_seconds = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
interval = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
proc_root = Path(sys.argv[6]) if len(sys.argv) > 6 else Path("/proc")
ignored_executables = {"iscriptevaluator.exe"}


def read_args(pid):
    try:
        raw = (proc_root / str(pid) / "cmdline").read_bytes()
    except (OSError, PermissionError):
        return []
    return [
        item.decode("utf-8", errors="replace")
        for item in raw.split(b"\0")
        if item
    ]


def read_parent_pid(pid):
    try:
        content = (proc_root / str(pid) / "status").read_text(
            encoding="utf-8", errors="replace"
        )
    except (OSError, PermissionError):
        return None

    for line in content.splitlines():
        if not line.startswith("PPid:"):
            continue
        fields = line.split()
        if len(fields) < 2:
            return None
        try:
            return int(fields[1])
        except ValueError:
            return None
    return None


def read_executable(pid):
    try:
        return os.readlink(proc_root / str(pid) / "exe")
    except (OSError, PermissionError):
        return ""


def processes():
    result = {}
    try:
        entries = list(proc_root.iterdir())
    except (OSError, PermissionError):
        return result

    for entry in entries:
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        ppid = read_parent_pid(pid)
        if ppid is None:
            continue
        args = read_args(pid)
        result[pid] = {
            "pid": pid,
            "ppid": ppid,
            "args": args,
            "cmdline": " ".join(args),
            "executable": read_executable(pid),
        }
    return result


def exe_name(argument):
    cleaned = argument.strip("\"'").replace("\\", "/")
    position = cleaned.lower().rfind(".exe")
    if position < 0:
        return None
    return Path(cleaned[: position + 4]).name


def real_launch_process(process):
    cmdline = process["cmdline"]
    if "SteamLaunch" not in cmdline:
        return False
    if f"AppId={appid}" not in process["args"]:
        return False
    if "Install=1" in process["args"]:
        return False
    if "iscriptevaluator.exe" in cmdline.lower():
        return False
    return True


def target_executable(process):
    for argument in reversed(process["args"]):
        name = exe_name(argument)
        if not name or name.lower() in ignored_executables:
            continue
        return name
    return None


def descendants(root_pid, snapshot):
    found = set()
    tracked = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, process in snapshot.items():
            if pid in tracked or process["ppid"] not in tracked:
                continue
            tracked.add(pid)
            found.add(pid)
            changed = True
    return found


def game_process(launch_process, target, snapshot):
    target_lower = target.lower()
    for pid in sorted(descendants(launch_process["pid"], snapshot)):
        process = snapshot.get(pid)
        if not process:
            continue
        executable = process["executable"].lower()
        if "wine-preloader" not in executable and "wine64-preloader" not in executable:
            continue
        names = [name for name in (exe_name(arg) for arg in process["args"]) if name]
        if not names or names[0].lower() != target_lower:
            continue
        return process
    return None


def detect_runtime():
    snapshot = processes()
    launches = [process for process in snapshot.values() if real_launch_process(process)]
    launches.sort(
        key=lambda process: (
            "waitforexitandrun" in process["cmdline"].lower(),
            process["pid"],
        ),
        reverse=True,
    )

    for launch in launches:
        target = target_executable(launch)
        if not target:
            continue
        game = game_process(launch, target, snapshot)
        if game:
            return game["pid"], target
    return None


def emit(runtime):
    pid, target = runtime
    print(f"{pid}\t{target}")


if mode == "once":
    runtime = detect_runtime()
    if runtime is None:
        sys.exit(2)
    emit(runtime)
    sys.exit(0)

if mode != "wait":
    print(f"Unknown detector mode: {mode}", file=sys.stderr)
    sys.exit(3)

started = time.monotonic()
stable_pid = None
stable_since = None
last_runtime = None

while time.monotonic() - started < timeout:
    runtime = detect_runtime()
    if runtime is None:
        stable_pid = None
        stable_since = None
        last_runtime = None
    else:
        pid, _target = runtime
        if pid != stable_pid:
            stable_pid = pid
            stable_since = time.monotonic()
        last_runtime = runtime
        if (
            stable_since is not None
            and time.monotonic() - stable_since >= stable_seconds
        ):
            emit(last_runtime)
            sys.exit(0)
    time.sleep(interval)

sys.exit(2)
'''


def _shell_join(parts):
    return " ".join(shlex.quote(str(part)) for part in parts)


def _validate_game(game):
    validate_steam_appid(game.appid)

    if not game.trainer_path or not Path(game.trainer_path).is_file():
        raise RuntimeError("No valid trainer is configured for this game.")

    if not game.prefix or not Path(game.prefix).is_dir():
        raise RuntimeError("No valid Proton compatdata directory was found.")

    if not game.proton_path:
        raise RuntimeError("No Proton version was detected for this game.")

    proton_executable = Path(game.proton_path) / "proton"
    if not proton_executable.is_file():
        raise RuntimeError(
            f"The Proton executable does not exist: {proton_executable}"
        )

    return proton_executable


def _build_standard_script(game, steam_info, proton_executable):
    appid = validate_steam_appid(game.appid)
    steam_root = steam_info.get("install_path")
    launch_prefix = steam_info.get("launch_prefix") or ()

    if not steam_root:
        raise RuntimeError("The Steam installation path was not found.")

    if not launch_prefix:
        raise RuntimeError("A supported Steam launch command was not found.")

    launch_command = [
        *launch_prefix,
        f"steam://rungameid/{appid}"
    ]

    values = {
        "appid": shlex.quote(appid),
        "game_name": shlex.quote(str(game.name)),
        "prefix": shlex.quote(str(Path(game.prefix))),
        "prefix_pfx": shlex.quote(str(Path(game.prefix) / "pfx")),
        "steam_root": shlex.quote(str(steam_root)),
        "proton": shlex.quote(str(proton_executable)),
        "trainer": shlex.quote(str(Path(game.trainer_path))),
        "launch": _shell_join(launch_command)
    }

    header = f'''#!/usr/bin/env bash
set -euo pipefail

# Exported by TrainerBridge.
# Absolute paths are used. Re-export this script after moving Steam,
# the game library, Proton, or the trainer.

APPID={values["appid"]}
GAME_NAME={values["game_name"]}
COMPATDATA={values["prefix"]}
WINEPREFIX_PATH={values["prefix_pfx"]}
STEAM_ROOT={values["steam_root"]}
PROTON={values["proton"]}
TRAINER={values["trainer"]}
SESSION_TIMEOUT={SESSION_TIMEOUT_SECONDS}
SESSION_STABLE_SECONDS={SESSION_STABLE_SECONDS}
TRAINER_DELAY={TRAINER_DELAY_SECONDS}

command -v python3 >/dev/null || {{ echo "python3 was not found." >&2; exit 1; }}
[[ -x "$PROTON" ]] || {{ echo "Proton executable not found: $PROTON" >&2; exit 1; }}
[[ -f "$TRAINER" ]] || {{ echo "Trainer not found: $TRAINER" >&2; exit 1; }}
[[ -d "$WINEPREFIX_PATH" ]] || {{ echo "Proton prefix not found: $WINEPREFIX_PATH" >&2; exit 1; }}

DETECTOR_FILE="$(mktemp)"
trap 'rm -f "$DETECTOR_FILE"' EXIT

cat > "$DETECTOR_FILE" <<'TB_GAME_DETECTOR_PY'
'''

    footer = f'''
TB_GAME_DETECTOR_PY

find_game_runtime() {{
    python3 "$DETECTOR_FILE" "$APPID" once
}}

RUNTIME="$(find_game_runtime || true)"

if [[ -z "$RUNTIME" ]]; then
    echo "Launching $GAME_NAME through Steam..."
    {values["launch"]} >/dev/null 2>&1 &
fi

echo "Waiting for the actual game executable to remain stable..."
if ! RUNTIME="$(python3 "$DETECTOR_FILE" "$APPID" wait "$SESSION_TIMEOUT" "$SESSION_STABLE_SECONDS")"; then
    echo "$GAME_NAME was not detected within $SESSION_TIMEOUT seconds." >&2
    exit 1
fi

IFS=$'\\t' read -r GAME_PID GAME_EXECUTABLE <<< "$RUNTIME"
if [[ -z "${{GAME_PID:-}}" || -z "${{GAME_EXECUTABLE:-}}" ]]; then
    echo "TrainerBridge detected an invalid game runtime." >&2
    exit 1
fi

echo "Game detected: $GAME_EXECUTABLE (PID $GAME_PID)."
echo "Waiting $TRAINER_DELAY more seconds..."
sleep "$TRAINER_DELAY"

export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_DIR="$STEAM_ROOT"

exec "$PROTON" runinprefix "$TRAINER"
'''

    return "".join((header, _STANDARD_GAME_DETECTOR, footer))


_FLATPAK_INSTANCE_FINDER = r'''import json
import subprocess
import sys
from pathlib import Path

appid, flatpak_id, probe = sys.argv[1:4]

try:
    output = subprocess.check_output(
        ["flatpak", "ps", "--columns=instance,pid,application"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
except Exception:
    sys.exit(1)

for line in output.splitlines():
    fields = line.split()
    if len(fields) < 3 or fields[2] != flatpak_id:
        continue

    instance, host_pid = fields[0], fields[1]

    try:
        arguments = [
            item.decode("utf-8", errors="replace")
            for item in (Path("/proc") / host_pid / "cmdline").read_bytes().split(b"\0")
            if item
        ]
    except OSError:
        continue

    game_path = ""
    for index, argument in enumerate(arguments):
        if (
            argument.endswith("/proton")
            and index + 2 < len(arguments)
            and arguments[index + 1] == "waitforexitandrun"
        ):
            game_path = arguments[index + 2]
            break

    if not game_path:
        continue

    result = subprocess.run(
        ["flatpak", "enter", instance, "/usr/bin/python3", "-c", probe, appid],
        capture_output=True,
        text=True,
        errors="replace",
    )
    if result.returncode != 0:
        continue

    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        continue

    candidate_name = Path(game_path.replace("\\", "/")).name.lower()
    detected_name = str(payload.get("game_executable") or "").lower()
    if candidate_name and detected_name and candidate_name != detected_name:
        continue

    print(instance)
    sys.exit(0)

sys.exit(2)
'''


def _build_flatpak_script(game, steam_info, proton_executable):
    appid = validate_steam_appid(game.appid)
    steam_root = steam_info.get("install_path")
    launch_prefix = steam_info.get("launch_prefix") or ()

    if not steam_root or not launch_prefix:
        raise RuntimeError("The Steam Flatpak installation was not found.")

    launch_command = [
        *launch_prefix,
        f"steam://rungameid/{appid}"
    ]

    header = f'''#!/usr/bin/env bash
set -euo pipefail

# Exported by TrainerBridge.
# Steam Flatpak edition. Absolute paths are used.

APPID={shlex.quote(appid)}
GAME_NAME={shlex.quote(str(game.name))}
COMPATDATA={shlex.quote(str(Path(game.prefix)))}
STEAM_ROOT={shlex.quote(str(steam_root))}
PROTON={shlex.quote(str(proton_executable))}
TRAINER={shlex.quote(str(Path(game.trainer_path)))}
STEAM_FLATPAK_ID={shlex.quote(STEAM_FLATPAK_APP_ID)}
SESSION_TIMEOUT={SESSION_TIMEOUT_SECONDS}
SESSION_STABLE_SECONDS={SESSION_STABLE_SECONDS}
TRAINER_DELAY={TRAINER_DELAY_SECONDS}

command -v flatpak >/dev/null || {{ echo "flatpak was not found." >&2; exit 1; }}
[[ -x "$PROTON" ]] || {{ echo "Proton executable not found: $PROTON" >&2; exit 1; }}
[[ -f "$TRAINER" ]] || {{ echo "Trainer not found: $TRAINER" >&2; exit 1; }}

PROBE_FILE="$(mktemp)"
FINDER_FILE="$(mktemp)"
LAUNCHER_FILE="$(mktemp)"
trap 'rm -f "$PROBE_FILE" "$FINDER_FILE" "$LAUNCHER_FILE"' EXIT

cat > "$PROBE_FILE" <<'TB_PROBE_PY'
'''

    between_probe_and_finder = '''
TB_PROBE_PY

cat > "$FINDER_FILE" <<'TB_FINDER_PY'
'''

    between_finder_and_launcher = '''
TB_FINDER_PY

cat > "$LAUNCHER_FILE" <<'TB_LAUNCHER_PY'
'''

    footer = f'''
TB_LAUNCHER_PY

find_game_instance() {{
    python3 "$FINDER_FILE" "$APPID" "$STEAM_FLATPAK_ID" "$(cat "$PROBE_FILE")"
}}

INSTANCE="$(find_game_instance || true)"

if [[ -z "$INSTANCE" ]]; then
    echo "Launching $GAME_NAME through Steam Flatpak..."
    {_shell_join(launch_command)} >/dev/null 2>&1 &
fi

echo "Waiting for the Steam Flatpak Proton session..."
deadline=$((SECONDS + SESSION_TIMEOUT))
stable_seconds=0

while (( SECONDS < deadline )); do
    current_instance="$(find_game_instance || true)"

    if [[ -n "$current_instance" ]]; then
        if [[ "$current_instance" == "${{INSTANCE:-}}" ]]; then
            stable_seconds=$((stable_seconds + 1))
        else
            INSTANCE="$current_instance"
            stable_seconds=1
        fi

        if (( stable_seconds >= SESSION_STABLE_SECONDS )); then
            break
        fi
    else
        INSTANCE=""
        stable_seconds=0
    fi

    sleep 1
done

if [[ -z "$INSTANCE" ]] || (( stable_seconds < SESSION_STABLE_SECONDS )); then
    echo "The Steam Flatpak Proton session was not detected within $SESSION_TIMEOUT seconds." >&2
    exit 1
fi

echo "Proton session detected. Waiting $TRAINER_DELAY more seconds..."
sleep "$TRAINER_DELAY"

if ! flatpak enter "$INSTANCE" sh -c 'test -r "$1"' sh "$TRAINER"; then
    echo "Steam Flatpak cannot read the trainer file." >&2
    echo "Grant read-only access in TrainerBridge and restart Steam." >&2
    exit 1
fi

exec flatpak enter "$INSTANCE" /usr/bin/python3 -c "$(cat "$LAUNCHER_FILE")" \
    "$APPID" "$PROTON" "$TRAINER" "$STEAM_ROOT" "$COMPATDATA"
'''

    return "".join(
        (
            header,
            _SESSION_PROBE,
            between_probe_and_finder,
            _FLATPAK_INSTANCE_FINDER,
            between_finder_and_launcher,
            _TRAINER_LAUNCHER,
            footer,
        )
    )


def build_launch_script(game):
    proton_executable = _validate_game(game)
    steam_info = get_steam_info()

    if steam_info.get("kind") == "flatpak":
        return _build_flatpak_script(game, steam_info, proton_executable)

    return _build_standard_script(game, steam_info, proton_executable)
