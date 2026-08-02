import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from core.host_process import host_environment
from core.steam import STEAM_FLATPAK_APP_ID


@dataclass(frozen=True)
class FlatpakSteamSession:
    appid: str
    instance: str
    host_pid: int
    source_pid: int
    source_cmdline: str
    game_executable: str
    game_path: str
    compatdata_path: str | None = None


_SESSION_PROBE = r'''
import json
import sys
from pathlib import Path

appid = sys.argv[1]
ignored = {"iscriptevaluator.exe"}
candidates = []


def read_environment(path):
    raw = path.read_bytes()
    result = {}
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        result[key.decode("utf-8", errors="surrogateescape")] = value.decode(
            "utf-8", errors="surrogateescape"
        )
    return result


def exe_name(argument):
    cleaned = argument.strip("\"'").replace("\\", "/")
    position = cleaned.lower().rfind(".exe")
    if position < 0:
        return None
    return Path(cleaned[: position + 4]).name


for proc_dir in Path("/proc").iterdir():
    if not proc_dir.name.isdigit():
        continue

    try:
        environment = read_environment(proc_dir / "environ")
        process_appid = (
            environment.get("STEAM_COMPAT_APP_ID")
            or environment.get("SteamAppId")
            or environment.get("SteamGameId")
        )
        if process_appid != appid:
            continue

        arguments = [
            item.decode("utf-8", errors="replace")
            for item in (proc_dir / "cmdline").read_bytes().split(b"\0")
            if item
        ]
    except (OSError, PermissionError):
        continue

    cmdline = " ".join(arguments)
    lowered = cmdline.lower()

    if "install=1" in lowered or "iscriptevaluator.exe" in lowered:
        continue

    if f"SteamLaunch AppId={appid}" not in cmdline:
        continue

    target = None
    game_path = ""
    for argument in reversed(arguments):
        name = exe_name(argument)
        if not name or name.lower() in ignored:
            continue
        target = name
        game_path = argument.strip("\"'")
        break

    score = 0
    if f"SteamLaunch AppId={appid}" in cmdline:
        score += 100
    if "waitforexitandrun" in lowered:
        score += 50
    if any(argument.endswith("/proton") for argument in arguments):
        score += 25
    if target:
        score += 10

    candidates.append(
        {
            "score": score,
            "pid": int(proc_dir.name),
            "cmdline": cmdline,
            "game_executable": target or "",
            "game_path": game_path,
            "compatdata_path": environment.get("STEAM_COMPAT_DATA_PATH"),
        }
    )

if not candidates:
    sys.exit(2)

candidates.sort(key=lambda item: (item["score"], item["pid"]), reverse=True)
print(json.dumps(candidates[0]))
'''


_TRAINER_LAUNCHER = r'''
import os
import sys
from pathlib import Path

appid, proton, trainer, steam_root, compatdata = sys.argv[1:6]


def read_environment(path):
    raw = path.read_bytes()
    result = {}
    for item in raw.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        result[key.decode("utf-8", errors="surrogateescape")] = value.decode(
            "utf-8", errors="surrogateescape"
        )
    return result


candidates = []
for proc_dir in Path("/proc").iterdir():
    if not proc_dir.name.isdigit():
        continue

    try:
        environment = read_environment(proc_dir / "environ")
        process_appid = (
            environment.get("STEAM_COMPAT_APP_ID")
            or environment.get("SteamAppId")
            or environment.get("SteamGameId")
        )
        if process_appid != appid:
            continue

        cmdline = " ".join(
            item.decode("utf-8", errors="replace")
            for item in (proc_dir / "cmdline").read_bytes().split(b"\0")
            if item
        )
    except (OSError, PermissionError):
        continue

    lowered = cmdline.lower()
    if "install=1" in lowered or "iscriptevaluator.exe" in lowered:
        continue

    if f"SteamLaunch AppId={appid}" not in cmdline:
        continue

    score = 0
    if f"SteamLaunch AppId={appid}" in cmdline:
        score += 100
    if "waitforexitandrun" in lowered:
        score += 50
    if environment.get("STEAM_COMPAT_DATA_PATH", "").rstrip("/") == compatdata.rstrip("/"):
        score += 25

    candidates.append((score, int(proc_dir.name), environment))

if not candidates:
    print("TrainerBridge could not read the live Steam Flatpak game environment.", file=sys.stderr)
    sys.exit(2)

candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
environment = candidates[0][2]

environment["SteamAppId"] = appid
environment["SteamGameId"] = appid
environment["STEAM_COMPAT_APP_ID"] = appid
environment["STEAM_COMPAT_DATA_PATH"] = compatdata
environment["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = steam_root
environment["STEAM_DIR"] = steam_root

# These variables are useful to Steam's own launcher but point to runtime
# objects that are not valid for a second process entered from the host.
environment.pop("LD_AUDIT", None)
environment.pop("LD_PRELOAD", None)

if not environment.get("HOME"):
    environment["HOME"] = str(Path.home())

os.execvpe(
    proton,
    [proton, "runinprefix", trainer],
    environment,
)
'''


def _flatpak_command():
    return shutil.which("flatpak")


def _read_cmdline(pid):
    try:
        return [
            item.decode("utf-8", errors="replace")
            for item in Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
            if item
        ]
    except (OSError, PermissionError):
        return []


def _host_game_path(arguments):
    for index, argument in enumerate(arguments):
        if (
            argument.endswith("/proton")
            and index + 2 < len(arguments)
            and arguments[index + 1] == "waitforexitandrun"
        ):
            return arguments[index + 2]
    return ""


def list_steam_flatpak_instances():
    flatpak = _flatpak_command()
    if not flatpak:
        return []

    try:
        result = subprocess.run(
            [flatpak, "ps", "--columns=instance,pid,application"],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            env=host_environment(),
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    instances = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 3 or fields[2] != STEAM_FLATPAK_APP_ID:
            continue
        try:
            host_pid = int(fields[1])
        except ValueError:
            continue
        arguments = _read_cmdline(host_pid)
        instances.append(
            {
                "instance": fields[0],
                "host_pid": host_pid,
                "arguments": arguments,
                "game_path": _host_game_path(arguments),
            }
        )

    instances.sort(
        key=lambda item: (
            bool(item["game_path"]),
            item["host_pid"],
        ),
        reverse=True,
    )
    return instances



def steam_flatpak_has_running_game():
    return any(
        bool(instance.get("game_path"))
        for instance in list_steam_flatpak_instances()
    )


def running_steam_flatpak_can_read(path):
    flatpak = _flatpak_command()
    if not flatpak:
        return False

    instances = list_steam_flatpak_instances()
    if not instances:
        return True

    path = str(Path(path).expanduser().resolve())

    for instance in instances:
        try:
            result = subprocess.run(
                [
                    flatpak,
                    "enter",
                    instance["instance"],
                    "sh",
                    "-c",
                    'test -r "$1"',
                    "sh",
                    path,
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=host_environment(),
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if result.returncode == 0:
            return True

    return False


def find_flatpak_game_session(appid):
    flatpak = _flatpak_command()
    if not flatpak:
        return None

    appid = str(appid)

    for candidate in list_steam_flatpak_instances():
        # The game-specific Pressure Vessel instance has the Proton launch in
        # its host-side command line. Entering that exact instance is required
        # when the trainer is started later.
        if not candidate["game_path"]:
            continue

        try:
            result = subprocess.run(
                [
                    flatpak,
                    "enter",
                    candidate["instance"],
                    "/usr/bin/python3",
                    "-c",
                    _SESSION_PROBE,
                    appid,
                ],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                env=host_environment(),
                timeout=8,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if result.returncode != 0:
            continue

        try:
            payload = json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, TypeError, ValueError, json.JSONDecodeError):
            continue

        candidate_name = Path(candidate["game_path"].replace("\\", "/")).name.lower()
        detected_name = str(payload.get("game_executable") or "").lower()
        if candidate_name and detected_name and candidate_name != detected_name:
            continue

        return FlatpakSteamSession(
            appid=appid,
            instance=candidate["instance"],
            host_pid=candidate["host_pid"],
            source_pid=int(payload.get("pid") or 0),
            source_cmdline=str(payload.get("cmdline") or ""),
            game_executable=str(payload.get("game_executable") or candidate_name),
            game_path=str(payload.get("game_path") or candidate["game_path"]),
            compatdata_path=payload.get("compatdata_path"),
        )

    return None


def build_flatpak_trainer_command(game, flatpak_instance, steam_root):
    flatpak = _flatpak_command()
    if not flatpak:
        raise RuntimeError("The flatpak command was not found.")

    if not flatpak_instance:
        raise RuntimeError(
            "The running Steam Flatpak game sandbox was not found."
        )

    proton = Path(game.proton_path) / "proton"
    compatdata = Path(game.prefix)

    return [
        flatpak,
        "enter",
        str(flatpak_instance),
        "/usr/bin/python3",
        "-c",
        _TRAINER_LAUNCHER,
        str(game.appid),
        str(proton),
        str(game.trainer_path),
        str(steam_root),
        str(compatdata),
    ]


def _effective_filesystems():
    flatpak = _flatpak_command()
    if not flatpak:
        return []

    try:
        result = subprocess.run(
            [flatpak, "info", "--show-permissions", STEAM_FLATPAK_APP_ID],
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
            env=host_environment(),
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    filesystems = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped.startswith("filesystems="):
            continue
        value = stripped.split("=", 1)[1]
        filesystems.extend(item for item in value.split(";") if item)

    return filesystems


def _filesystem_permission_path(token):
    home = Path.home().resolve()

    if token.startswith("~/"):
        return home / token[2:]

    xdg_roots = {
        "xdg-data": Path(
            os.environ.get("XDG_DATA_HOME", home / ".local" / "share")
        ),
        "xdg-config": Path(
            os.environ.get("XDG_CONFIG_HOME", home / ".config")
        ),
        "xdg-cache": Path(
            os.environ.get("XDG_CACHE_HOME", home / ".cache")
        ),
    }

    for name, root in xdg_roots.items():
        if token == name:
            return root
        if token.startswith(name + "/"):
            return root / token[len(name) + 1:]

    if token.startswith("/"):
        return Path(token)

    return None


def _path_is_within(path, allowed):
    try:
        path.relative_to(allowed)
        return True
    except ValueError:
        return False


def steam_flatpak_can_read(path):
    path = Path(path).expanduser().resolve()
    permissions = _effective_filesystems()

    denied_paths = []
    allowed_paths = []
    broad_access = False

    for permission in permissions:
        raw_token = permission.split(":", 1)[0]
        denied = raw_token.startswith("!")
        token = raw_token[1:] if denied else raw_token

        if token in {"host", "home"}:
            if not denied:
                broad_access = True
            continue

        resolved = _filesystem_permission_path(token)
        if resolved is None:
            continue

        try:
            resolved = resolved.expanduser().resolve()
        except OSError:
            continue

        if denied:
            denied_paths.append(resolved)
        else:
            allowed_paths.append(resolved)

    if any(_path_is_within(path, denied) for denied in denied_paths):
        return False

    if broad_access:
        return True

    return any(_path_is_within(path, allowed) for allowed in allowed_paths)


def grant_steam_flatpak_read_access(path):
    flatpak = _flatpak_command()
    if not flatpak:
        raise RuntimeError("The flatpak command was not found.")

    path = Path(path).expanduser().resolve()
    result = subprocess.run(
        [
            flatpak,
            "override",
            "--user",
            f"--filesystem={path}:ro",
            STEAM_FLATPAK_APP_ID,
        ],
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
        env=host_environment(),
        timeout=15,
    )

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            message
            or "Steam Flatpak's read-only folder permission could not be added."
        )


def restart_steam_flatpak():
    flatpak = _flatpak_command()
    if not flatpak:
        return

    try:
        subprocess.run(
            [flatpak, "kill", STEAM_FLATPAK_APP_ID],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=host_environment(),
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if not list_steam_flatpak_instances():
            break
        time.sleep(0.1)
