import shutil
import subprocess


class SteamGameLauncher:

    def build_command(self, appid):

        steam_uri = (
            f"steam://rungameid/{appid}"
        )

        steam_command = shutil.which(
            "steam"
        )

        if steam_command:

            return [
                steam_command,
                steam_uri
            ]

        flatpak_command = shutil.which(
            "flatpak"
        )

        if flatpak_command:

            flatpak_check = subprocess.run(
                [
                    flatpak_command,
                    "info",
                    "com.valvesoftware.Steam"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if flatpak_check.returncode == 0:

                return [
                    flatpak_command,
                    "run",
                    "com.valvesoftware.Steam",
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
            "Steam konnte nicht gestartet werden. "
            "Weder Steam, Flatpak-Steam noch xdg-open wurden gefunden."
        )


    def launch(self, appid):

        command = self.build_command(
            appid
        )

        print("Steam-Startbefehl:")
        print(" ".join(command))
        print()

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        return process
