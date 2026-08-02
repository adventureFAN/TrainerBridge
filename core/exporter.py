import shlex
from pathlib import Path

from core.steam import get_steam_info


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
    local environment_file

    for environment_file in /proc/[0-9]*/environ; do
        [[ -r "$environment_file" ]] || continue

        if grep -azFxq "SteamAppId=$APPID" "$environment_file" 2>/dev/null \
            && grep -azFxq "WINEPREFIX=$WINEPREFIX_PATH" "$environment_file" 2>/dev/null; then
            return 0
        fi
    done

    return 1
}}

if ! session_detected; then
    echo "Launching $GAME_NAME through Steam..."
    {values["launch"]} >/dev/null 2>&1 &
fi

echo "Waiting for the Proton session..."
deadline=$((SECONDS + 120))
stable_seconds=0

while (( SECONDS < deadline )); do
    if session_detected; then
        stable_seconds=$((stable_seconds + 1))
        if (( stable_seconds >= 5 )); then
            break
        fi
    else
        stable_seconds=0
    fi

    sleep 1
done

if (( stable_seconds < 5 )); then
    echo "The Proton session was not detected within 120 seconds." >&2
    exit 1
fi

echo "Proton session detected. Waiting 8 more seconds..."
sleep 8

export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_DIR="$STEAM_ROOT"

exec "$PROTON" runinprefix "$TRAINER"
'''
