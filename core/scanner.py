from core.steam import get_steam_libraries
from core.games import find_games
from core.proton import apply_proton_info
from core.trainer_manager import apply_trainer_info


def determine_status(game):

    # Kein Proton = natives Linux-Spiel oder App
    if not game.proton_name:
        return "NATIVE"


    # Proton vorhanden + Trainer vorhanden
    if game.trainer_path:
        return "READY_WITH_TRAINER"


    # Proton vorhanden + Prefix vorhanden
    if game.prefix:
        return "READY"


    # Proton bekannt, aber noch kein Prefix
    return "PROTON_DETECTED"



def scan_all_games():

    libraries = get_steam_libraries()

    games = find_games(libraries)

    for game in games:

        # Proton-Informationen suchen
        apply_proton_info(game)

        # Trainer laden
        apply_trainer_info(game)

        # Status bestimmen
        game.status = determine_status(game)


    return games
