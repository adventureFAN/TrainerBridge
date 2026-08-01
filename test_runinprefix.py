import os
import subprocess
import sys
import time

from core.process_monitor import ProcessMonitor
from core.scanner import scan_all_games
from core.steam import get_steam_info


APPID = "2679460"

GAME_EXIT_TIMEOUT = 60


def find_game(games, appid):

    for game in games:

        if game.appid == appid:
            return game

    return None


print("=== TrainerBridge runinprefix-Test ===")
print()

print(
    "Metaphor muss bereits vollständig laufen."
)

print(
    "Starte das Spiel normal über Steam "
    "und warte bis zum Hauptmenü."
)

print()


monitor = ProcessMonitor()

runtime = monitor.get_runtime(
    APPID
)


if not runtime:

    print(
        "Die echte METAPHOR.exe wurde nicht gefunden."
    )

    print(
        "Starte Metaphor zuerst normal über Steam "
        "und führe den Test danach erneut aus."
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
        f"Kein Spielprofil für AppID {APPID} gefunden."
    )

    sys.exit(1)


if not game.trainer_path:

    print(
        "Für Metaphor wurde kein Trainer gefunden."
    )

    sys.exit(1)


if not game.prefix:

    print(
        "Für Metaphor wurde kein Proton-Prefix gefunden."
    )

    sys.exit(1)


if not game.proton_path:

    print(
        "Für Metaphor wurde keine Proton-Version gefunden."
    )

    sys.exit(1)


proton_executable = (
    game.proton_path /
    "proton"
)


if not proton_executable.exists():

    print(
        "Die Proton-Startdatei wurde nicht gefunden:"
    )

    print(
        proton_executable
    )

    sys.exit(1)


steam_info = get_steam_info()

steam_install_path = steam_info[
    "install_path"
]


if not steam_install_path:

    print(
        "Der Steam-Installationspfad wurde nicht gefunden."
    )

    sys.exit(1)


environment = os.environ.copy()

environment[
    "STEAM_COMPAT_DATA_PATH"
] = str(game.prefix)

environment[
    "STEAM_COMPAT_CLIENT_INSTALL_PATH"
] = str(steam_install_path)


command = [
    str(proton_executable),
    "runinprefix",
    str(game.trainer_path)
]


print()
print("Spiel:")
print(game.name)

print()
print("Game-PID:")
print(runtime.game_pid)

print()
print("Trainer:")
print(game.trainer_path)

print()
print("Testbefehl:")

print(
    f'STEAM_COMPAT_DATA_PATH="{game.prefix}"'
)

print(
    f'STEAM_COMPAT_CLIENT_INSTALL_PATH="'
    f'{steam_install_path}"'
)

print(
    f'"{proton_executable}" '
    f'runinprefix '
    f'"{game.trainer_path}"'
)

print()
print(
    "Starte Trainer mit runinprefix..."
)


trainer_process = subprocess.Popen(
    command,
    env=environment
)


print()
print(
    "Trainer-Prozess gestartet."
)

print(
    "PID:",
    trainer_process.pid
)


time.sleep(3)

return_code = trainer_process.poll()


if return_code is not None:

    print()
    print(
        "Der Trainer-Prozess wurde zu früh beendet."
    )

    print(
        "Rückgabecode:",
        return_code
    )

    sys.exit(1)


print()
print(
    "Der Trainer-Prozess läuft."
)

print()
print(
    "Prüfe jetzt, ob der Trainer Metaphor erkennt."
)

print()
print(
    "Schließe danach ZUERST nur den Trainer."
)

print(
    "Das Skript wartet auf dessen Ende..."
)


try:

    trainer_return_code = (
        trainer_process.wait()
    )

except KeyboardInterrupt:

    print()
    print(
        "Test wurde abgebrochen."
    )

    sys.exit(1)


print()
print(
    "Trainer wurde beendet."
)

print(
    "Rückgabecode:",
    trainer_return_code
)

print()
print(
    "Schließe Metaphor jetzt normal über das Spielmenü."
)

print(
    f"TrainerBridge beobachtet den Spielprozess "
    f"für maximal {GAME_EXIT_TIMEOUT} Sekunden."
)


exit_start = time.monotonic()


while (
    time.monotonic() - exit_start
    < GAME_EXIT_TIMEOUT
):

    current_runtime = monitor.get_runtime(
        APPID
    )


    if not current_runtime:

        print()
        print(
            "Metaphor wurde vollständig und sauber beendet."
        )

        print()
        print(
            "Der runinprefix-Test war erfolgreich."
        )

        sys.exit(0)


    time.sleep(1)


print()
print(
    "Metaphor wurde innerhalb des Zeitlimits "
    "nicht vollständig beendet."
)

print()
print(
    "Noch erkannter Prozess:"
)

print(
    monitor.get_runtime(APPID)
)

print()
print(
    "Bitte noch nicht gewaltsam über das Skript beenden."
)

print(
    "Die Ausgabe zeigt uns, dass das Problem "
    "auch mit runinprefix besteht."
)

sys.exit(1)
