from pathlib import Path


STEAM_COMPAT_CLIENT_INSTALL_PATH = Path.home() / ".local/share/Steam"


def build_trainer_command(game):

    if not game.trainer_path:
        return None


    if not game.prefix:
        return None


    if not game.proton_path:
        return None


    command = [
        f'STEAM_COMPAT_DATA_PATH="{game.prefix}"',
        f'STEAM_COMPAT_CLIENT_INSTALL_PATH="{STEAM_COMPAT_CLIENT_INSTALL_PATH}"',
        f'"{game.proton_path}/proton"',
        "run",
        f'"{game.trainer_path}"'
    ]


    return " \\\n".join(command)
