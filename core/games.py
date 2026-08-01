from pathlib import Path
import vdf

from core.models import GameProfile


def is_ignored_app(name):

    ignored_names = [
        "Proton",
        "Steam Linux Runtime",
        "Steamworks Common Redistributables"
    ]

    for ignored in ignored_names:
        if name.startswith(ignored):
            return True

    return False


def find_games(libraries):

    games = []

    found_appids = set()

    for library in libraries:

        steamapps = library / "steamapps"

        if not steamapps.exists():
            continue

        for manifest in steamapps.glob("appmanifest_*.acf"):

            try:
                with open(manifest, "r", encoding="utf-8") as f:
                    data = vdf.load(f)

                app = data["AppState"]

                appid = app["appid"]
                name = app["name"]

                if appid in found_appids:
                    continue

                found_appids.add(appid)

                if is_ignored_app(name):
                    continue

                prefix = (
                    library /
                    "steamapps" /
                    "compatdata" /
                    appid
                )

                game = GameProfile(
                    name=name,
                    appid=appid,
                    library=library,
                    prefix=prefix if prefix.exists() else None
                )

                games.append(game)

            except Exception as e:
                print(
                    f"Fehler bei {manifest}: {e}"
                )

    return games
