from pathlib import Path
import vdf


def find_library_files():
    return [
        Path.home() / ".steam/steam/steamapps/libraryfolders.vdf",
        Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
    ]


def get_steam_libraries():
    libraries = []

    for file in find_library_files():
        if file.exists():

            with open(file, "r", encoding="utf-8") as f:
                data = vdf.load(f)

            folders = data["libraryfolders"]

            for key, value in folders.items():
                if "path" in value:
                    libraries.append(value["path"])

    return list(set(libraries))


if __name__ == "__main__":
    libs = get_steam_libraries()

    print("Steam Bibliotheken:")
    for lib in libs:
        print("-", lib)
