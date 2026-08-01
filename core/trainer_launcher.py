import subprocess
from pathlib import Path

from core.host_process import host_environment


class TrainerLauncher:

    def __init__(
        self,
        steam_install_path: Path,
        steam_kind=None
    ):

        if steam_install_path is None:

            raise RuntimeError(
                "The Steam installation path was not found."
            )

        self.steam_install_path = Path(
            steam_install_path
        )

        self.steam_kind = steam_kind


    def validate_game(
        self,
        game
    ):

        if not game.trainer_path:

            raise RuntimeError(
                "No trainer has been configured for this game."
            )

        if not game.trainer_path.exists():

            raise RuntimeError(
                "The trainer file does not exist: "
                f"{game.trainer_path}"
            )

        if not game.prefix:

            raise RuntimeError(
                "No Proton prefix was found for this game."
            )

        if not game.prefix.exists():

            raise RuntimeError(
                "The Proton prefix does not exist: "
                f"{game.prefix}"
            )

        if not game.proton_path:

            raise RuntimeError(
                "No Proton version was found for this game."
            )

        proton_executable = (
            game.proton_path
            / "proton"
        )

        if not proton_executable.exists():

            raise RuntimeError(
                "The Proton executable does not exist: "
                f"{proton_executable}"
            )

        return proton_executable


    def build_command(
        self,
        game
    ):

        proton_executable = self.validate_game(
            game
        )

        return [
            str(proton_executable),
            "runinprefix",
            str(game.trainer_path)
        ]


    def build_environment(
        self,
        game
    ):

        environment = host_environment()

        environment[
            "STEAM_COMPAT_DATA_PATH"
        ] = str(game.prefix)

        environment[
            "STEAM_COMPAT_CLIENT_INSTALL_PATH"
        ] = str(self.steam_install_path)

        environment[
            "STEAM_DIR"
        ] = str(self.steam_install_path)

        return environment


    def launch(
        self,
        game
    ):

        command = self.build_command(
            game
        )

        environment = self.build_environment(
            game
        )

        print()

        if self.steam_kind:

            print(
                "Steam installation type: "
                f"{self.steam_kind}"
            )

        print("Trainer command:")
        print(
            f'STEAM_COMPAT_DATA_PATH="{game.prefix}"'
        )
        print(
            "STEAM_COMPAT_CLIENT_INSTALL_PATH="
            f'"{self.steam_install_path}"'
        )
        print(
            f'"{command[0]}" runinprefix '
            f'"{game.trainer_path}"'
        )
        print()

        return subprocess.Popen(
            command,
            env=environment
        )
