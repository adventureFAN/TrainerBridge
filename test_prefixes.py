from core.games import find_games
from core.steam import get_steam_libraries
from core.proton import apply_proton_info
from core.trainer_manager import apply_trainer_info


print()
print("=== Proton Trainer Manager Prefix Diagnose ===")
print()


libraries = get_steam_libraries()

games = find_games(libraries)


for game in games:

    apply_proton_info(game)

    apply_trainer_info(game)

    print(game.name)
    print("AppID:", game.appid)

    print()
    print("Proton:")
    
    if game.proton_name:
        print(
            game.proton_name,
            "(",
            game.proton_version,
            ")"
        )
    else:
        print("Nicht erkannt")


    print()
    print("Prefix Objekt:")

    if game.prefix:
        print(game.prefix)

        if game.prefix.exists():
            print("Existiert: JA")
        else:
            print("Existiert: NEIN")

    else:
        print("Kein Prefix gefunden")


    print()
    print("Trainer:")

    if game.trainer_path:
        print(game.trainer_path)
    else:
        print("Keiner")


    print()
    print("-" * 50)
