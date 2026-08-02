import shlex
from pathlib import Path

from core.steam import get_steam_info


SESSION_TIMEOUT_SECONDS = 60
SESSION_STABLE_SECONDS = 5
TRAINER_DELAY_SECONDS = 8


def _shell_join(parts):
    return " ".join(shlex.quote(str(part)) for part in parts)


def build_launch_script(game):
    if not game.trainer_path or not Path(game.trainer_path).is_file():
        raise RuntimeError("No valid trainer is configured for this game.")

    if not game.prefix or not Path(game.prefix).is_dir():
        raise RuntimeError("No valid Proton compatdata directory was found.")

    if not game.proton_path:
        raise RuntimeError("No Proton version was detected for this game.")

    proton_executable = Path(game.proton_path) / "proton"
    if not proton_executable.is_file():
        raise RuntimeError(f"The Proton executable does not exist: {proton_executable}")

    steam_info = get_steam_info()
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

        if grep -aziFq "iscriptevaluator.exe" "$cmdline_file" 2>/dev/null; then
            continue
        fi

        if grep -azFxq "Install=1" "$cmdline_file" 2>/dev/null; then
            continue
        fi

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
