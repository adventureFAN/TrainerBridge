import subprocess
import re


def get_processes():
    result = subprocess.run(
        ["ps", "-eo", "pid,ppid,args"],
        capture_output=True,
        text=True
    )

    return result.stdout.splitlines()


def get_steam_launches():

    processes = get_processes()

    found = []

    for line in processes:

        if "SteamLaunch AppId=" in line:

            parts = line.strip().split(None, 2)

            if len(parts) < 3:
                continue

            pid = parts[0]
            appid = re.search(r"AppId=(\d+)", line)

            if appid:
                found.append({
                    "pid": pid,
                    "appid": appid.group(1),
                    "command": parts[2]
                })

    return found


def get_children(parent_pid):

    processes = get_processes()

    children = []

    for line in processes:

        parts = line.strip().split(None, 2)

        if len(parts) < 3:
            continue

        pid = parts[0]
        ppid = parts[1]
        command = parts[2]

        if ppid == parent_pid:
            children.append({
                "pid": pid,
                "command": command
            })

    return children


def show_tree(pid, level=0):

    children = get_children(pid)

    for child in children:

        print(
            "   " * level
            + f"{child['pid']} -> {child['command']}"
        )

        show_tree(child["pid"], level + 1)


def main():

    print("=== TrainerBridge Process Tree Test ===")
    print()

    launches = get_steam_launches()

    for launch in launches:

        print("AppID:", launch["appid"])
        print("Root PID:", launch["pid"])
        print()

        print("Prozessbaum:")

        show_tree(launch["pid"], 1)

        print()
        print("-" * 60)


if __name__ == "__main__":
    main()
