import os
from pathlib import Path


def read_config_info(prefix):

    config = prefix / "config_info"

    if not config.exists():
        return None

    with open(config, "r", encoding="utf-8") as f:
        lines = [
            line.strip()
            for line in f.readlines()
            if line.strip()
        ]

    if not lines:
        return None

    return {
        "version": lines[0],
        "config": lines
    }


def _is_supported_proton_root(candidate):

    proton_executable = candidate / "proton"

    if not proton_executable.is_file():
        return False

    if not os.access(proton_executable, os.X_OK):
        return False

    parent = candidate.parent

    if parent.name == "compatibilitytools.d":
        return True

    return (
        parent.name == "common"
        and parent.parent.name == "steamapps"
    )


def _find_proton_root_from_path(path):

    current = path

    if current.is_file():
        current = current.parent

    for candidate in (
        current,
        *current.parents
    ):

        if _is_supported_proton_root(candidate):
            return candidate

    return None


def detect_proton_path(config):

    if not config:
        return None

    candidates = {}

    for line in config["config"]:

        path = Path(line).expanduser()

        if not path.is_absolute():
            continue

        proton_root = _find_proton_root_from_path(
            path
        )

        if proton_root is None:
            continue

        try:
            identity = proton_root.resolve()
        except OSError:
            identity = proton_root.absolute()

        candidates.setdefault(
            identity,
            proton_root
        )

    if len(candidates) != 1:
        return None

    return next(iter(candidates.values()))


def apply_proton_info(game):

    if not game.prefix:
        return game

    config = read_config_info(game.prefix)

    if not config:
        return game

    proton_path = detect_proton_path(config)

    if proton_path:
        game.proton_path = proton_path
        game.proton_name = proton_path.name

    game.proton_version = config["version"]

    return game
