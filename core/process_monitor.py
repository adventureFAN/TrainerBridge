import subprocess
import time


class GameRuntime:

    def __init__(self, appid, pid, steam_process):

        self.appid = appid
        self.pid = pid
        self.steam_process = steam_process


    def __repr__(self):

        return (
            f"GameRuntime("
            f"appid={self.appid}, "
            f"pid={self.pid}, "
            f"steam_process='{self.steam_process[:80]}...'"
            f")"
        )



class ProcessMonitor:


    def __init__(self):
        pass


    def _get_processes(self):

        result = subprocess.run(
            ["ps", "-eo", "pid,ppid,args"],
            capture_output=True,
            text=True
        )

        return result.stdout.splitlines()



    def find_game(self, appid):

        for line in self._get_processes():

            if "SteamLaunch" not in line:
                continue

            if f"AppId={appid}" not in line:
                continue

            return line.strip()

        return None



    def _extract_pid(self, process_line):

        parts = process_line.split()

        if not parts:
            return None

        try:

            return int(parts[0])

        except ValueError:

            return None



    def get_runtime(self, appid):

        process = self.find_game(appid)

        if not process:
            return None


        pid = self._extract_pid(process)


        return GameRuntime(
            appid=appid,
            pid=pid,
            steam_process=process
        )



    def wait_for_game(
        self,
        appid,
        timeout=120,
        interval=1
    ):

        start = time.time()


        while time.time() - start < timeout:

            runtime = self.get_runtime(appid)


            if runtime:

                return runtime


            time.sleep(interval)


        return None
