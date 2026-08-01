import sys
import time

from core.scanner import scan_all_games
from core.session_manager import TrainerSessionManager


APPID = "2679460"


def find_game(games, appid):

    for game in games:

        if game.appid == appid:
            return game

    return None


print("=== TrainerBridge Vollständiger Starttest ===")
print()

print("Scanne Steam-Spiele...")

games = scan_all_games()

game = find_game(
    games,
    APPID
)


if not game:

    print()
    print(
        f"Kein Spiel mit der AppID {APPID} gefunden."
    )

    sys.exit(1)


print()
print("Spiel:")
print(game.name)

print()
print("AppID:")
print(game.appid)

print()
print("Status:")
print(game.status)

print()
print("Prefix:")
print(game.prefix)

print()
print("Proton:")
print(game.proton_path)

print()
print("Trainer:")
print(game.trainer_path)


if not game.trainer_path:

    print()
    print(
        "Für dieses Spiel wurde kein Trainer importiert."
    )

    sys.exit(1)


session_manager = TrainerSessionManager()


print()
print("Starte TrainerBridge-Sitzung...")
print()


try:

    session = session_manager.start(
        game,
        timeout=120,
        trainer_delay=8
    )

except Exception as error:

    print()
    print("Start fehlgeschlagen:")
    print(error)

    sys.exit(1)


trainer_process = session[
    "trainer_process"
]


print()
print("Trainer-Prozess wurde gestartet.")
print("PID:", trainer_process.pid)


if session["game_was_running"]:

    print(
        "Das Spiel lief bereits vor dem Start."
    )

else:

    print(
        "Das Spiel wurde von TrainerBridge gestartet."
    )


time.sleep(3)

return_code = trainer_process.poll()


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
