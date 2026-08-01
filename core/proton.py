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


def detect_proton_path(config):

    if not config:
        return None

    for line in config["config"]:

        if "/compatibilitytools.d/" in line:
            return Path(
                line.split("/files/")[0]
            )

        if "/steamapps/common/" in line:
            return Path(
                line.split("/files/")[0]
            )

    return None


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
