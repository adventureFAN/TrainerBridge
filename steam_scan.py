from pathlib import Path


def find_steam_libraries():
    possible_files = [
        Path.home() / ".steam/steam/steamapps/libraryfolders.vdf",
        Path.home() / ".local/share/Steam/steamapps/libraryfolders.vdf"
    ]

    found_files = []

    for file in possible_files:
        if file.exists():
            found_files.append(file)

    print("Gefundene Steam-Dateien:")
    for file in found_files:
        print("-", file)


if __name__ == "__main__":
    find_steam_libraries()
