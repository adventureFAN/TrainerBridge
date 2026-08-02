import shlex
from pathlib import Path

from core.flatpak_steam import _SESSION_PROBE, _TRAINER_LAUNCHER
from core.steam import STEAM_FLATPAK_APP_ID, get_steam_info


SESSION_TIMEOUT_SECONDS = 60
SESSION_STABLE_SECONDS = 5
TRAINER_DELAY_SECONDS = 4


def _shell_join(parts):
    return " ".join(shlex.quote(str(part)) for part in parts)


def _validate_game(game):
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
    steam_root = steam_info.get("install_path")
    launch_prefix = steam_info.get("launch_prefix") or ()

    if not steam_root:
        raise RuntimeError("The Steam installation path was not found.")

    if not launch_prefix:
        raise RuntimeError("A supported Steam launch command was not found.")

    launch_command = [
        *launch_prefix,
        f"steam://rungameid/{game.appid}"
    ]

    values = {
        "appid": shlex.quote(str(game.appid)),
        "game_name": shlex.quote(str(game.name)),
        "prefix": shlex.quote(str(Path(game.prefix))),
        "prefix_pfx": shlex.quote(str(Path(game.prefix) / "pfx")),
        "steam_root": shlex.quote(str(steam_root)),
        "proton": shlex.quote(str(proton_executable)),
        "trainer": shlex.quote(str(Path(game.trainer_path))),
        "launch": _shell_join(launch_command)
    }

    return f'''#!/usr/bin/env bash
set -euo pipefail

# Exported by TrainerBridge for {game.name}
# Absolute paths are used. Re-export this script after moving Steam,
# the game library, Proton, or the trainer.

APPID={values["appid"]}
GAME_NAME={values["game_name"]}
COMPATDATA={values["prefix"]}
WINEPREFIX_PATH={values["prefix_pfx"]}
STEAM_ROOT={values["steam_root"]}
PROTON={values["proton"]}
TRAINER={values["trainer"]}

[[ -x "$PROTON" ]] || {{ echo "Proton executable not found: $PROTON" >&2; exit 1; }}
[[ -f "$TRAINER" ]] || {{ echo "Trainer not found: $TRAINER" >&2; exit 1; }}
[[ -d "$WINEPREFIX_PATH" ]] || {{ echo "Proton prefix not found: $WINEPREFIX_PATH" >&2; exit 1; }}

session_detected() {{
    local cmdline_file

    for cmdline_file in /proc/[0-9]*/cmdline; do
        [[ -r "$cmdline_file" ]] || continue

        grep -azFq "SteamLaunch" "$cmdline_file" 2>/dev/null || continue
        grep -azFxq "AppId=$APPID" "$cmdline_file" 2>/dev/null || continue
        grep -aziFq "iscriptevaluator.exe" "$cmdline_file" 2>/dev/null && continue
        grep -azFxq "Install=1" "$cmdline_file" 2>/dev/null && continue

        return 0
    done

    return 1
}}

if ! session_detected; then
    echo "Launching $GAME_NAME through Steam..."
    {values["launch"]} >/dev/null 2>&1 &
fi

SESSION_TIMEOUT={SESSION_TIMEOUT_SECONDS}
SESSION_STABLE_SECONDS={SESSION_STABLE_SECONDS}
TRAINER_DELAY={TRAINER_DELAY_SECONDS}

echo "Waiting for the Proton session..."
deadline=$((SECONDS + SESSION_TIMEOUT))
stable_seconds=0

while (( SECONDS < deadline )); do
    if session_detected; then
        stable_seconds=$((stable_seconds + 1))
        if (( stable_seconds >= SESSION_STABLE_SECONDS )); then
            break
        fi
    else
        stable_seconds=0
    fi

    sleep 1
done

if (( stable_seconds < SESSION_STABLE_SECONDS )); then
    echo "The Proton session was not detected within $SESSION_TIMEOUT seconds." >&2
    exit 1
fi

echo "Proton session detected. Waiting $TRAINER_DELAY more seconds..."
sleep "$TRAINER_DELAY"

export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_DIR="$STEAM_ROOT"

exec "$PROTON" runinprefix "$TRAINER"
'''


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
    steam_root = steam_info.get("install_path")
    launch_prefix = steam_info.get("launch_prefix") or ()

    if not steam_root or not launch_prefix:
        raise RuntimeError("The Steam Flatpak installation was not found.")

    launch_command = [
        *launch_prefix,
        f"steam://rungameid/{game.appid}"
    ]

    header = f'''#!/usr/bin/env bash
set -euo pipefail

# Exported by TrainerBridge for {game.name}
# Steam Flatpak edition. Absolute paths are used.

APPID={shlex.quote(str(game.appid))}
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
