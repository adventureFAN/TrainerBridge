import time
from pathlib import Path


APPID = "2679460"

OBSERVATION_TIME = 120
POLL_INTERVAL = 0.5


SYSTEM_WINDOWS_PROCESSES = {
    "conhost.exe",
    "explorer.exe",
    "plugplay.exe",
    "rpcss.exe",
    "services.exe",
    "start.exe",
    "steam.exe",
    "steamwebhelper.exe",
    "svchost.exe",
    "winedevice.exe",
    "wineboot.exe",
    "winemenubuilder.exe",
    "wineserver.exe",
}


def read_cmdline(pid):

    path = Path(
        f"/proc/{pid}/cmdline"
    )

    try:

        raw = path.read_bytes()

    except (
        FileNotFoundError,
        PermissionError,
        ProcessLookupError
    ):

        return ""


    if not raw:
        return ""


    parts = raw.split(
        b"\0"
    )

    decoded = []

    for part in parts:

        if not part:
            continue

        decoded.append(
            part.decode(
                "utf-8",
                errors="replace"
            )
        )


    return " ".join(
        decoded
    )


def read_parent_pid(pid):

    path = Path(
        f"/proc/{pid}/status"
    )

    try:

        content = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

    except (
        FileNotFoundError,
        PermissionError,
        ProcessLookupError
    ):

        return None


    for line in content.splitlines():

        if not line.startswith("PPid:"):
            continue

        parts = line.split()

        if len(parts) < 2:
            return None

        try:

            return int(
                parts[1]
            )

        except ValueError:

            return None


    return None


def read_executable(pid):

    path = Path(
        f"/proc/{pid}/exe"
    )

    try:

        return str(
            path.resolve()
        )

    except (
        FileNotFoundError,
        PermissionError,
        ProcessLookupError,
        RuntimeError
    ):

        return ""


def get_process_snapshot():

    processes = {}


    for entry in Path("/proc").iterdir():

        if not entry.name.isdigit():
            continue

        pid = int(
            entry.name
        )

        parent_pid = read_parent_pid(
            pid
        )

        if parent_pid is None:
            continue

        processes[pid] = {
            "pid": pid,
            "ppid": parent_pid,
            "cmdline": read_cmdline(pid),
            "executable": read_executable(pid)
        }


    return processes


def find_steam_launch_processes(
    processes,
    appid
):

    roots = set()


    for pid, process in processes.items():

        cmdline = process[
            "cmdline"
        ]

        if "SteamLaunch" not in cmdline:
            continue

        if f"AppId={appid}" not in cmdline:
            continue

        roots.add(
            pid
        )


    return roots


def add_descendants(
    tracked_pids,
    processes
):

    changed = True


    while changed:

        changed = False


        for pid, process in processes.items():

            if pid in tracked_pids:
                continue

            if process["ppid"] not in tracked_pids:
                continue

            tracked_pids.add(
                pid
            )

            changed = True


def extract_exe_names(cmdline):

    names = []


    for part in cmdline.split():

        cleaned = part.strip(
            "\"'"
        )

        lower = cleaned.lower()


        if ".exe" not in lower:
            continue


        exe_end = lower.find(
            ".exe"
        ) + 4

        exe_value = cleaned[
            :exe_end
        ]

        names.append(
            Path(
                exe_value.replace(
                    "\\",
                    "/"
                )
            ).name
        )


    return names


def is_game_exe_candidate(
    process
):

    exe_names = extract_exe_names(
        process["cmdline"]
    )


    if not exe_names:
        return False


    for exe_name in exe_names:

        if exe_name.lower() not in SYSTEM_WINDOWS_PROCESSES:

            return True


    return False


def print_process(
    process,
    first_seen
):

    pid = process["pid"]
    ppid = process["ppid"]

    cmdline = process[
        "cmdline"
    ]

    executable = process[
        "executable"
    ]


    marker = "PROZESS"


    if is_game_exe_candidate(process):

        marker = "EXE-KANDIDAT"


    print()
    print(
        f"[{marker}]"
    )

    print(
        f"PID:  {pid}"
    )

    print(
        f"PPID: {ppid}"
    )

    print(
        f"Seit: {first_seen:.1f} Sekunden"
    )

    print(
        f"Linux-Programm: {executable}"
    )

    print(
        f"Befehl: {cmdline}"
    )


def main():

    print(
        "=== TrainerBridge Prozessdiagnose ==="
    )

    print()

    print(
        f"Gesuchte AppID: {APPID}"
    )

    print()

    print(
        "Starte Metaphor jetzt normal über Steam."
    )

    print(
        "Der Trainer darf dabei nicht laufen."
    )

    print()

    print(
        "Die Diagnose wartet auf Steam und beobachtet "
        "anschließend den Prozessbaum."
    )

    print()


    start_time = time.monotonic()

    tracked_pids = set()
    printed_pids = set()
    first_seen_times = {}

    launch_found = False


    try:

        while (
            time.monotonic() - start_time
            < OBSERVATION_TIME
        ):

            now = time.monotonic()

            processes = get_process_snapshot()

            roots = find_steam_launch_processes(
                processes,
                APPID
            )


            if roots and not launch_found:

                launch_found = True

                print()
                print(
                    "Steam-Startprozess gefunden."
                )

                print(
                    "Beobachte jetzt dessen Kindprozesse..."
                )


            tracked_pids.update(
                roots
            )


            existing_tracked = {
                pid
                for pid in tracked_pids
                if pid in processes
            }

            tracked_pids = existing_tracked


            add_descendants(
                tracked_pids,
                processes
            )


            for pid in sorted(
                tracked_pids
            ):

                if pid not in first_seen_times:

                    first_seen_times[pid] = now


                if pid in printed_pids:
                    continue


                process = processes.get(
                    pid
                )


                if not process:
                    continue


                alive_for = (
                    now -
                    first_seen_times[pid]
                )


                print_process(
                    process,
                    alive_for
                )

                printed_pids.add(
                    pid
                )


            time.sleep(
                POLL_INTERVAL
            )


    except KeyboardInterrupt:

        print()
        print()
        print(
            "Diagnose wurde beendet."
        )

        return


    print()
    print()
    print(
        "Beobachtungszeit beendet."
    )


if __name__ == "__main__":

    main()
