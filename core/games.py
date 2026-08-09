import vdf

from core.models import GameProfile
from core.validation import (
    build_steam_game_path,
    validate_steam_appid
)


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

                appid = validate_steam_appid(
                    app["appid"]
                )
                name = app["name"]
                install_dir = app.get("installdir")

                game_path = None

                if install_dir:
                    try:
                        game_path = build_steam_game_path(
                            library,
                            install_dir
                        )
                    except ValueError:
                        print(
                            "Ignored an unsafe Steam installdir; "
                            "the game-folder action is disabled for this entry."
                        )

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
                        ),
                        game_path=game_path
                    )
                )

            except Exception as error:

                print(
                    f"Failed to read {manifest}: {error}"
                )

    return games
