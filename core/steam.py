from pathlib import Path
import vdf


def find_steam_config():

    possible = [
        Path.home() / ".steam/steam/steamapps/libraryfolders.vdf",
        Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf",
        Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/libraryfolders.vdf"
    ]

    for path in possible:

        if path.exists():
            return path

    return None



def find_steam_install():

    possible = [
        Path.home() / ".steam/steam",
        Path.home() / ".local/share/Steam",
        Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam"
    ]


    for path in possible:

        if path.exists():

            return path


    return None



def get_steam_libraries():

    config = find_steam_config()

    if not config:
        return []


    with open(config, "r", encoding="utf-8") as f:

        data = vdf.load(f)


    libraries = []


    for value in data["libraryfolders"].values():

        if "path" in value:

            libraries.append(
                Path(value["path"])
            )


    return libraries



def get_steam_info():

    return {
        "install_path": find_steam_install(),
        "libraries": get_steam_libraries()
    }
