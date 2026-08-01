from core.games import find_games
from core.proton import apply_proton_info
from core.steam import get_steam_info
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

    steam_info = get_steam_info()

    steam_install_path = steam_info[
        "install_path"
    ]

    if not steam_install_path:

        print(
            "No supported Steam data directory was found."
        )

        return []

    print(
        "Detected Steam installation: "
        f"{steam_info['display_name']}"
    )

    print(
        "Steam data directory: "
        f"{steam_install_path}"
    )

    libraries = steam_info[
        "libraries"
    ]

    for library in libraries:

        print(
            f"Steam library: {library}"
        )

    games = find_games(
        libraries
    )

    for game in games:

        # Proton-Informationen suchen
        apply_proton_info(game)

        # Trainer laden
        apply_trainer_info(game)

        # Status bestimmen
        game.status = determine_status(game)

    return games
