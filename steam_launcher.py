import subprocess


def launch_game(appid):

    command = [
        "steam",
        f"steam://rungameid/{appid}"
    ]

    subprocess.Popen(command)


if __name__ == "__main__":

    launch_game("2679460")
