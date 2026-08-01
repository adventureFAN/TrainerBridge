import time

from core.game_launcher import SteamGameLauncher
from core.process_monitor import ProcessMonitor
from core.steam import get_steam_info
from core.trainer_launcher import TrainerLauncher


class TrainerSessionManager:

    def __init__(self):

        self.game_launcher = SteamGameLauncher()
        self.process_monitor = ProcessMonitor()


    def launch_game(
        self,
        game,
        timeout=120
    ):

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

            print(
                "Starting the game through Steam..."
            )

            game_process = self.game_launcher.launch(
                game.appid
            )

        print(
            "Waiting for the actual game executable "
            "to remain stable..."
        )

        runtime = self.process_monitor.wait_for_game(
            game.appid,
            timeout=timeout,
            interval=0.5,
            stable_seconds=5
        )

        if not runtime:

            raise TimeoutError(
                f"{game.name} was not detected within "
                f"{timeout} seconds."
            )

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
        game
    ):

        runtime = self.process_monitor.get_runtime(
            game.appid
        )

        if not runtime:

            raise RuntimeError(
                "The actual game executable is not running. "
                "Launch and verify the game before starting "
                "the trainer."
            )

        steam_info = get_steam_info()

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

        print()
        print(
            "Starting the trainer inside the running game prefix..."
        )

        trainer_process = trainer_launcher.launch(
            game
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
        timeout=120,
        trainer_delay=8
    ):

        game_session = self.launch_game(
            game,
            timeout=timeout
        )

        if trainer_delay > 0:

            print()
            print(
                f"Waiting another {trainer_delay} seconds "
                "for the game to finish starting..."
            )

            time.sleep(
                trainer_delay
            )

        trainer_session = self.launch_trainer(
            game
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
