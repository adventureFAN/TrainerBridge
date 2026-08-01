from pathlib import Path
import vdf


def get_steam_libraries():
    libraries = [
        Path("/run/media/system/Spiele_1/SteamLibrary"),
        Path("/run/media/system/Spiele_2/SteamLibrary"),
        Path.home() / ".local/share/Steam",
        Path.home() / ".steam/steam"
    ]

    return [x for x in libraries if x.exists()]


def find_games():

    games = []

    for library in get_steam_libraries():

        steamapps = library / "steamapps"

        if not steamapps.exists():
            continue

        for manifest in steamapps.glob("appmanifest_*.acf"):

            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = vdf.load(f)

                app = data["AppState"]

                appid = app["appid"]

                prefix = library / "steamapps" / "compatdata" / appid

                games.append({
                    "name": app["name"],
                    "appid": appid,
                    "library": str(library),
                    "prefix": str(prefix) if prefix.exists() else None
                })

            except Exception as e:
                print("Fehler bei:", manifest)
                print(e)

    return games


if __name__ == "__main__":

    games = find_games()

    print("Gefundene Spiele:")
    print()

    for game in games:

        print(
            f'{game["name"]} '
            f'(ID: {game["appid"]})'
        )

        if game["prefix"]:
            print("   Prefix:", game["prefix"])
        else:
            print("   Kein Proton Prefix")

        print()
