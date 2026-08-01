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

        for manifest in steamapps.glob(
            "appmanifest_*.acf"
        ):

            try:

                with open(
                    manifest,
                    "r",
                    encoding="utf-8"
                ) as file:

                    data = vdf.load(file)

                app = data["AppState"]

                appid = app["appid"]
                name = app["name"]

                if appid in found_appids:
                    continue

                found_appids.add(appid)

                if is_ignored_app(name):
                    continue

                prefix = (
                    library
                    / "steamapps"
                    / "compatdata"
                    / appid
                )

                games.append(
                    GameProfile(
                        name=name,
                        appid=appid,
                        library=library,
                        prefix=(
                            prefix
                            if prefix.exists()
                            else None
                        )
                    )
                )

            except Exception as error:

                print(
                    f"Failed to read {manifest}: {error}"
                )

    return games
