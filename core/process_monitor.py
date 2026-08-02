import time
from pathlib import Path

from core.flatpak_steam import find_flatpak_game_session
from core.steam import get_steam_info


class GameRuntime:

    def __init__(
        self,
        appid,
        launch_pid,
        game_pid,
        game_executable,
        steam_process,
        steam_kind=None,
        flatpak_instance=None,
        flatpak_source_pid=None
    ):

        self.appid = appid

        self.launch_pid = launch_pid
        self.game_pid = game_pid

        # Kompatibilität mit bisherigem Code
        self.pid = game_pid

        self.game_executable = game_executable
        self.steam_process = steam_process
        self.steam_kind = steam_kind
        self.flatpak_instance = flatpak_instance
        self.flatpak_source_pid = flatpak_source_pid


    def __repr__(self):

        return (
            f"GameRuntime("
            f"appid={self.appid}, "
            f"launch_pid={self.launch_pid}, "
            f"game_pid={self.game_pid}, "
            f"game_executable='{self.game_executable}'"
            f")"
        )


class ProcessMonitor:

    def __init__(self, steam_kind=None):

        self.steam_kind = steam_kind


    def _current_steam_kind(self):

        if self.steam_kind:
            return self.steam_kind

        return get_steam_info().get("kind")


    def _get_flatpak_runtime(self, appid):

        session = find_flatpak_game_session(appid)

        if session is None:
            return None

        return GameRuntime(
            appid=appid,
            launch_pid=session.source_pid,
            game_pid=session.host_pid,
            game_executable=session.game_executable,
            steam_process=session.source_cmdline,
            steam_kind="flatpak",
            flatpak_instance=session.instance,
            flatpak_source_pid=session.source_pid
        )


    def _read_process_args(self, pid):

        cmdline_path = Path(
            f"/proc/{pid}/cmdline"
        )

        try:

            raw = cmdline_path.read_bytes()

        except (
            FileNotFoundError,
            PermissionError,
            ProcessLookupError
        ):

            return []


        if not raw:
            return []


        args = []


        for part in raw.split(b"\0"):

            if not part:
                continue

            args.append(
                part.decode(
                    "utf-8",
                    errors="replace"
                )
            )


        return args


    def _read_parent_pid(self, pid):

        status_path = Path(
            f"/proc/{pid}/status"
        )

        try:

            content = status_path.read_text(
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


    def _read_executable(self, pid):

        executable_path = Path(
            f"/proc/{pid}/exe"
        )

        try:

            return str(
                executable_path.resolve()
            )

        except (
            FileNotFoundError,
            PermissionError,
            ProcessLookupError,
            RuntimeError
        ):

            return ""


    def _get_processes(self):

        processes = {}


        try:

            proc_entries = list(
                Path("/proc").iterdir()
            )

        except PermissionError:

            return processes


        for entry in proc_entries:

            if not entry.name.isdigit():
                continue

            pid = int(
                entry.name
            )

            parent_pid = self._read_parent_pid(
                pid
            )

            if parent_pid is None:
                continue

            args = self._read_process_args(
                pid
            )

            processes[pid] = {
                "pid": pid,
                "ppid": parent_pid,
                "args": args,
                "cmdline": " ".join(args),
                "executable": self._read_executable(pid)
            }


        return processes


    def _is_real_launch_process(
        self,
        process,
        appid
    ):

        cmdline = process[
            "cmdline"
        ]

        cmdline_lower = cmdline.lower()


        if "SteamLaunch" not in cmdline:
            return False

        if f"AppId={appid}" not in cmdline:
            return False


        # Steams vorbereitender Installationslauf
        if "Install=1" in process["args"]:
            return False


        # Kein echter Spielstart
        if "iscriptevaluator.exe" in cmdline_lower:
            return False


        return True


    def _find_launch_processes(
        self,
        processes,
        appid
    ):

        candidates = []


        for process in processes.values():

            if not self._is_real_launch_process(
                process,
                appid
            ):

                continue

            candidates.append(
                process
            )


        def sort_key(process):

            cmdline_lower = process[
                "cmdline"
            ].lower()

            has_waitforexitandrun = (
                "waitforexitandrun"
                in cmdline_lower
            )

            return (
                has_waitforexitandrun,
                process["pid"]
            )


        candidates.sort(
            key=sort_key,
            reverse=True
        )


        return candidates


    def _exe_name_from_argument(
        self,
        argument
    ):

        cleaned = argument.strip(
            "\"'"
        )

        normalized = cleaned.replace(
            "\\",
            "/"
        )

        lower = normalized.lower()

        exe_position = lower.rfind(
            ".exe"
        )


        if exe_position == -1:
            return None


        executable_path = normalized[
            :exe_position + 4
        ]


        return Path(
            executable_path
        ).name


    def _extract_exe_names(
        self,
        process
    ):

        names = []


        for argument in process["args"]:

            exe_name = self._exe_name_from_argument(
                argument
            )

            if exe_name:

                names.append(
                    exe_name
                )


        return names


    def _extract_target_executable(
        self,
        launch_process
    ):

        ignored_executables = {
            "iscriptevaluator.exe"
        }


        for argument in reversed(
            launch_process["args"]
        ):

            exe_name = self._exe_name_from_argument(
                argument
            )

            if not exe_name:
                continue

            if exe_name.lower() in ignored_executables:
                continue

            return exe_name


        return None


    def _get_descendants(
        self,
        root_pid,
        processes
    ):

        descendants = set()

        tracked = {
            root_pid
        }

        changed = True


        while changed:

            changed = False


            for pid, process in processes.items():

                if pid in tracked:
                    continue

                if process["ppid"] not in tracked:
                    continue

                tracked.add(
                    pid
                )

                descendants.add(
                    pid
                )

                changed = True


        return descendants


    def _is_wine_application_process(
        self,
        process
    ):

        executable = process[
            "executable"
        ].lower()


        return (
            "wine-preloader" in executable
            or
            "wine64-preloader" in executable
        )


    def _find_game_process(
        self,
        launch_process,
        target_executable,
        processes
    ):

        descendants = self._get_descendants(
            launch_process["pid"],
            processes
        )

        target_lower = target_executable.lower()


        for pid in sorted(descendants):

            process = processes.get(
                pid
            )

            if not process:
                continue


            if not self._is_wine_application_process(
                process
            ):

                continue


            exe_names = self._extract_exe_names(
                process
            )


            if not exe_names:
                continue


            # Wichtig:
            #
            # Beim Proton-Hilfsprozess lautet die Reihenfolge:
            #
            # steam.exe
            # METAPHOR.exe
            #
            # Beim echten Spielprozess dagegen:
            #
            # METAPHOR.exe
            #
            # Deshalb muss die erste Windows-EXE
            # der erwarteten Spiel-EXE entsprechen.

            first_executable = exe_names[
                0
            ].lower()


            if first_executable != target_lower:
                continue


            return process


        return None


    def get_runtime(self, appid):

        if self._current_steam_kind() == "flatpak":
            return self._get_flatpak_runtime(appid)

        processes = self._get_processes()

        launch_processes = (
            self._find_launch_processes(
                processes,
                appid
            )
        )


        for launch_process in launch_processes:

            target_executable = (
                self._extract_target_executable(
                    launch_process
                )
            )


            if not target_executable:
                continue


            game_process = self._find_game_process(
                launch_process,
                target_executable,
                processes
            )


            if not game_process:
                continue


            return GameRuntime(
                appid=appid,
                launch_pid=launch_process["pid"],
                game_pid=game_process["pid"],
                game_executable=target_executable,
                steam_process=launch_process["cmdline"],
                steam_kind=self._current_steam_kind()
            )


        return None


    def find_game(self, appid):

        runtime = self.get_runtime(
            appid
        )


        if not runtime:
            return None


        return runtime.steam_process


    def wait_for_game(
        self,
        appid,
        timeout=60,
        interval=0.5,
        stable_seconds=5,
        cancel_event=None
    ):

        start_time = time.monotonic()

        stable_pid = None
        stable_since = None


        while (
            time.monotonic() - start_time
            < timeout
        ):

            if (
                cancel_event is not None
                and
                cancel_event.is_set()
            ):

                return None

            runtime = self.get_runtime(
                appid
            )


            if not runtime:

                stable_pid = None
                stable_since = None

                if cancel_event is None:

                    time.sleep(
                        interval
                    )

                elif cancel_event.wait(interval):

                    return None

                continue


            if runtime.game_pid != stable_pid:

                stable_pid = runtime.game_pid
                stable_since = time.monotonic()


            elif (
                stable_since is not None
                and
                time.monotonic() - stable_since
                >= stable_seconds
            ):

                return runtime


            if cancel_event is None:

                time.sleep(
                    interval
                )

            elif cancel_event.wait(interval):

                return None


        return None
