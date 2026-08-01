import subprocess
import time
import re


def get_processes():
    result = subprocess.run(
        ["ps", "-eo", "pid,ppid,args"],
        capture_output=True,
        text=True
    )

    return result.stdout.splitlines()


def find_steam_launches():

    processes = get_processes()

    games = []

    for line in processes:

        if "SteamLaunch AppId=" in line:

            match = re.search(r"AppId=(\d+)", line)

            if match:
                parts = line.strip().split(None, 2)

                games.append({
                    "pid": parts[0],
                    "appid": match.group(1),
                    "command": parts[2]
                })

    return games


def find_proton_processes():

    processes = get_processes()

    proton = []

    for line in processes:

        if "/proton " in line or " proton " in line:

            proton.append(line.strip())

    return proton


def find_windows_exes():

    processes = get_processes()

    exes = []

    ignored = [
        "steam.exe",
        "services.exe",
        "explorer.exe",
        "wineserver",
        "winedevice",
        "rpcss"
    ]

    for line in processes:

        lower = line.lower()

        if ".exe" not in lower:
            continue

        ignore = False

        for item in ignored:
            if item in lower:
                ignore = True

        if not ignore:
            exes.append(line.strip())

    return exes


def main():

    print("=== TrainerBridge Runtime Monitor Test ===")
    print()

    print("Suche laufende Steam Spiele...")
    print()

    games = find_steam_launches()

    if not games:
        print("Keine Steam Proton Spiele gefunden.")
        return

    for game in games:

        print("AppID:", game["appid"])
        print("Steam Prozess:")
        print(game["command"])
        print()

    print("-" * 60)

    print("Gefundene Proton Prozesse:")
    print()

    for proton in find_proton_processes():
        print(proton)

    print()

    print("-" * 60)

    print("Gefundene Windows EXE Prozesse:")
    print()

    for exe in find_windows_exes():
        print(exe)


if __name__ == "__main__":
    main()
