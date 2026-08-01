import os
import subprocess
from pathlib import Path


class TrainerLauncher:

    def __init__(self, steam_install_path: Path):

        if steam_install_path is None:
            raise RuntimeError(
                "Steam-Installationspfad wurde nicht gefunden."
            )

        self.steam_install_path = Path(
            steam_install_path
        )


    def validate_game(self, game):

        if not game.trainer_path:
            raise RuntimeError(
                "Für dieses Spiel wurde kein Trainer gefunden."
            )

        if not game.trainer_path.exists():
            raise RuntimeError(
                f"Trainer-Datei existiert nicht: {game.trainer_path}"
            )

        if not game.prefix:
            raise RuntimeError(
                "Für dieses Spiel wurde kein Proton-Prefix gefunden."
            )

        if not game.prefix.exists():
            raise RuntimeError(
                f"Proton-Prefix existiert nicht: {game.prefix}"
            )

        if not game.proton_path:
            raise RuntimeError(
                "Für dieses Spiel wurde keine Proton-Version gefunden."
            )

        proton_executable = (
            game.proton_path /
            "proton"
        )

        if not proton_executable.exists():
            raise RuntimeError(
                f"Proton-Startdatei existiert nicht: {proton_executable}"
            )

        return proton_executable


    def build_command(self, game):

        proton_executable = self.validate_game(
            game
        )

        return [
            str(proton_executable),
            "run",
            str(game.trainer_path)
        ]


    def build_environment(self, game):

        environment = os.environ.copy()

        environment[
            "STEAM_COMPAT_DATA_PATH"
        ] = str(game.prefix)

        environment[
            "STEAM_COMPAT_CLIENT_INSTALL_PATH"
        ] = str(self.steam_install_path)

        return environment


    def launch(self, game):

        command = self.build_command(
            game
        )

        environment = self.build_environment(
            game
        )

        print()
        print("Trainer-Befehl:")
        print(
            f'STEAM_COMPAT_DATA_PATH="{game.prefix}"'
        )
        print(
            f'STEAM_COMPAT_CLIENT_INSTALL_PATH="{self.steam_install_path}"'
        )
        print(
            f'"{command[0]}" run "{game.trainer_path}"'
        )
        print()

        process = subprocess.Popen(
            command,
            env=environment
        )

        return process
