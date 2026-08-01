from core.steam import get_steam_libraries
from core.games import find_games
from core.proton import apply_proton_info


libraries = get_steam_libraries()

games = find_games(libraries)


print()
print("Proton Spiele:")
print("=" * 40)


for game in games:

    if not game.prefix:
        continue

    apply_proton_info(game)

    print()
    print(game.name)
    print("AppID:", game.appid)
    print("Proton:", game.proton_name)
    print("Version:", game.proton_version)
    print("Pfad:", game.proton_path)
    print("Prefix:", game.prefix)
    print("-" * 40)
