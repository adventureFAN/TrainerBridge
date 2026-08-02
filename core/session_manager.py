import time

from core.game_launcher import SteamGameLauncher
from core.process_monitor import ProcessMonitor
from core.steam import get_steam_info
from core.trainer_launcher import TrainerLauncher


class LaunchCancelled(RuntimeError):
    """Raised when the user cancels an in-progress launch sequence."""


class TrainerSessionManager:

    def __init__(self):

        self.steam_info = get_steam_info()
        self.game_launcher = SteamGameLauncher()
        self.process_monitor = ProcessMonitor(
            steam_kind=self.steam_info.get("kind")
        )


    @staticmethod
    def _raise_if_cancelled(cancel_event):

        if cancel_event is not None and cancel_event.is_set():
            raise LaunchCancelled(
                "Launch cancelled. The game was left running."
            )


    @staticmethod
    def _wait_or_cancel(seconds, cancel_event):

        if seconds <= 0:
            return

        if cancel_event is None:
            time.sleep(seconds)
            return

        if cancel_event.wait(seconds):
            raise LaunchCancelled(
                "Launch cancelled. The game was left running."
            )


    @staticmethod
    def _stop_cancelled_trainer(trainer_process):

        if trainer_process is None:
            return

        try:
            if trainer_process.poll() is not None:
                return

            trainer_process.terminate()
            trainer_process.wait(timeout=3)

        except Exception:

            try:
                if trainer_process.poll() is None:
                    trainer_process.kill()
            except Exception:
                pass


    def launch_game(
        self,
        game,
        timeout=60,
        cancel_event=None
    ):

        self._raise_if_cancelled(cancel_event)

        print(
            f"Checking whether {game.name} is already running..."
        )

        runtime_before = self.process_monitor.get_runtime(
            game.appid
        )

        game_process = None
        game_was_running = runtime_before is not None

        if game_was_running:

            print(
                "The game is already running. "
                "Verifying the game executable..."
            )

        else:

            print(
                "The game is not running yet."
            )

            self._raise_if_cancelled(cancel_event)

            print(
                "Starting the game through Steam..."
            )

            game_process = self.game_launcher.launch(
                game.appid
            )

        self._raise_if_cancelled(cancel_event)

        print(
            "Waiting for the actual game executable "
            "to remain stable..."
        )

        runtime = self.process_monitor.wait_for_game(
            game.appid,
            timeout=timeout,
            interval=0.5,
            stable_seconds=5,
            cancel_event=cancel_event
        )

        if not runtime:

            self._raise_if_cancelled(cancel_event)

            raise TimeoutError(
                f"{game.name} was not detected within "
                f"{timeout} seconds."
            )

        self._raise_if_cancelled(cancel_event)

        print()
        print("Game detected:")
        print(runtime)

        return {
            "action": "game",
            "game": game,
            "runtime": runtime,
            "game_process": game_process,
            "trainer_process": None,
            "game_was_running": game_was_running
        }


    def launch_trainer(
        self,
        game,
        cancel_event=None
    ):

        self._raise_if_cancelled(cancel_event)

        runtime = self.process_monitor.get_runtime(
            game.appid
        )

        if not runtime:

            raise RuntimeError(
                "The actual game executable is not running. "
                "Launch and verify the game before starting "
                "the trainer."
            )

        steam_info = self.steam_info

        steam_install_path = steam_info[
            "install_path"
        ]

        if not steam_install_path:

            raise RuntimeError(
                "The Steam installation path was not found."
            )

        trainer_launcher = TrainerLauncher(
            steam_install_path,
            steam_kind=steam_info[
                "kind"
            ]
        )

        self._raise_if_cancelled(cancel_event)

        print()
        print(
            "Starting the trainer inside the running game prefix..."
        )

        trainer_process = trainer_launcher.launch(
            game,
            runtime=runtime
        )

        if cancel_event is not None and cancel_event.is_set():

            self._stop_cancelled_trainer(
                trainer_process
            )

            raise LaunchCancelled(
                "Launch cancelled. The game was left running."
            )

        trainer_started_at = time.monotonic()

        return {
            "action": "trainer",
            "game": game,
            "runtime": runtime,
            "game_process": None,
            "trainer_process": trainer_process,
            "trainer_started_at": trainer_started_at,
            "game_was_running": True
        }


    def start(
        self,
        game,
        timeout=60,
        trainer_delay=4,
        cancel_event=None
    ):

        game_session = self.launch_game(
            game,
            timeout=timeout,
            cancel_event=cancel_event
        )

        if trainer_delay > 0:

            print()
            print(
                f"Waiting another {trainer_delay} seconds "
                "for the game to finish starting..."
            )

            self._wait_or_cancel(
                trainer_delay,
                cancel_event
            )

        self._raise_if_cancelled(cancel_event)

        trainer_session = self.launch_trainer(
            game,
            cancel_event=cancel_event
        )

        return {
            "action": "combined",
            "game": game,
            "runtime": trainer_session["runtime"],
            "game_process": game_session["game_process"],
            "trainer_process": trainer_session["trainer_process"],
            "trainer_started_at": trainer_session["trainer_started_at"],
            "game_was_running": game_session["game_was_running"]
        }
