import sys
import time

from core.process_monitor import ProcessMonitor
from core.scanner import scan_all_games
from core.steam import get_steam_info
from core.trainer_launcher import TrainerLauncher


APPID = "2679460"


def find_game(games, appid):

    for game in games:

        if game.appid == appid:
            return game

    return None


print("=== TrainerBridge Starttest ===")
print()
print(
    "Metaphor muss bereits vollständig über Steam laufen."
)
print()


monitor = ProcessMonitor()

runtime = monitor.get_runtime(
    APPID
)


if not runtime:

    print(
        "Metaphor läuft noch nicht."
    )
    print()
    print(
        "Starte das Spiel über Steam, warte bis zum Hauptmenü "
        "und führe diesen Test danach erneut aus."
    )

    sys.exit(1)


print("Laufendes Spiel erkannt:")
print(runtime)
print()


print("Scanne Spielprofil...")

games = scan_all_games()

game = find_game(
    games,
    APPID
)


if not game:

    print(
        "Das Spielprofil für Metaphor wurde nicht gefunden."
    )

    sys.exit(1)


print()
print("Spiel:")
print(game.name)

print()
print("Prefix:")
print(game.prefix)

print()
print("Proton:")
print(game.proton_path)

print()
print("Trainer:")
print(game.trainer_path)


steam_info = get_steam_info()

steam_install_path = steam_info[
    "install_path"
]


if not steam_install_path:

    print()
    print(
        "Steam-Installationspfad wurde nicht gefunden."
    )

    sys.exit(1)


launcher = TrainerLauncher(
    steam_install_path
)


print()
print("Starte Trainer im laufenden Spiel-Prefix...")

try:

    process = launcher.launch(
        game
    )

except Exception as error:

    print()
    print("Trainer konnte nicht gestartet werden:")
    print(error)

    sys.exit(1)


print("Proton-Prozess gestartet.")
print("PID:", process.pid)


time.sleep(3)

return_code = process.poll()


if return_code is None:

    print()
    print(
        "Der Trainer-Prozess läuft."
    )

else:

    print()
    print(
        "Der Trainer-Prozess wurde früh beendet."
    )
    print(
        "Rückgabecode:",
        return_code
    )
