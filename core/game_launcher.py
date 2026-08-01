import shutil
import subprocess

from core.host_process import host_environment
from core.steam import get_steam_info


class SteamGameLauncher:

    def build_command(
        self,
        appid
    ):

        steam_uri = (
            f"steam://rungameid/{appid}"
        )

        steam_info = get_steam_info()

        launch_prefix = steam_info[
            "launch_prefix"
        ]

        if launch_prefix:

            return [
                *launch_prefix,
                steam_uri
            ]

        steam_command = shutil.which(
            "steam"
        )

        if steam_command:

            return [
                steam_command,
                steam_uri
            ]

        xdg_open_command = shutil.which(
            "xdg-open"
        )

        if xdg_open_command:

            return [
                xdg_open_command,
                steam_uri
            ]

        raise RuntimeError(
            "Steam could not be started. "
            "TrainerBridge could not find a supported "
            "Steam installation or xdg-open."
        )


    def launch(
        self,
        appid
    ):

        command = self.build_command(
            appid
        )

        print("Steam launch command:")
        print(" ".join(command))
        print()

        return subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=host_environment()
        )
