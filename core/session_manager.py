import time

from core.game_launcher import SteamGameLauncher
from core.process_monitor import ProcessMonitor
from core.steam import get_steam_info
from core.trainer_launcher import TrainerLauncher


class TrainerSessionManager:

    def __init__(self):

        self.game_launcher = SteamGameLauncher()
        self.process_monitor = ProcessMonitor()


    def start(
        self,
        game,
        timeout=120,
        trainer_delay=8
    ):

        print(
            f"Prüfe, ob {game.name} bereits läuft..."
        )

        runtime = self.process_monitor.get_runtime(
            game.appid
        )

        game_process = None
        game_was_running = runtime is not None


        if runtime:

            print(
                "Das Spiel läuft bereits."
            )

        else:

            print(
                "Das Spiel läuft noch nicht."
            )

            print(
                "Starte das Spiel über Steam..."
            )

            game_process = self.game_launcher.launch(
                game.appid
            )

            print(
                "Warte auf den Steam-/Proton-Start..."
            )

            runtime = self.process_monitor.wait_for_game(
                game.appid,
                timeout=timeout,
                interval=1
            )


        if not runtime:

            raise TimeoutError(
                f"{game.name} wurde innerhalb von "
                f"{timeout} Sekunden nicht erkannt."
            )


        print()
        print("Spiel wurde erkannt:")
        print(runtime)


        if trainer_delay > 0:

            print()
            print(
                f"Warte noch {trainer_delay} Sekunden, "
                "damit Proton vollständig gestartet ist..."
            )

            time.sleep(
                trainer_delay
            )


        steam_info = get_steam_info()

        steam_install_path = steam_info[
            "install_path"
        ]


        if not steam_install_path:

            raise RuntimeError(
                "Steam-Installationspfad wurde nicht gefunden."
            )


        trainer_launcher = TrainerLauncher(
            steam_install_path
        )


        print()
        print(
            "Starte den Trainer im laufenden Spiel-Prefix..."
        )

        trainer_process = trainer_launcher.launch(
            game
        )


        return {
            "game": game,
            "runtime": runtime,
            "game_process": game_process,
            "trainer_process": trainer_process,
            "game_was_running": game_was_running
        }
