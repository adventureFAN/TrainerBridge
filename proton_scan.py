from pathlib import Path
import vdf


def find_proton_locations():
    locations = []

    possible_paths = [
        Path.home() / ".steam/steam/compatibilitytools.d",
        Path.home() / ".local/share/Steam/compatibilitytools.d",
        Path.home() / ".steam/steam/steamapps/common",
        Path.home() / ".local/share/Steam/steamapps/common"
    ]

    # Zusätzlich alle gefundenen Steam Libraries durchsuchen
    steam_libraries = [
        Path("/run/media/system/Spiele_1/SteamLibrary"),
        Path("/run/media/system/Spiele_2/SteamLibrary")
    ]

    for library in steam_libraries:
        possible_paths.append(
            library / "steamapps/common"
        )

    for path in possible_paths:
        if path.exists():
            locations.append(path)

    return locations


def scan_proton():

    proton_versions = []

    for location in find_proton_locations():

        for item in location.iterdir():

            name = item.name

            if "Proton" not in name and "proton" not in name:
                continue

            if not item.is_dir():
                continue

            tool_version = "Unbekannt"

            # GE-Proton und andere Tools haben oft eine vdf
            vdf_file = item / "compatibilitytool.vdf"

            if vdf_file.exists():

                try:
                    with open(vdf_file, "r", encoding="utf-8") as f:
                        data = vdf.load(f)

                    tool = data.get("compatibilitytools", {})

                    for key in tool:
                        tool_version = key

                except Exception:
                    pass

            proton_versions.append({
                "name": name,
                "version": tool_version,
                "path": str(item)
            })

    return proton_versions


if __name__ == "__main__":

    proton = scan_proton()

    print("Gefundene Proton-Versionen:")
    print()

    for p in proton:
        print("✓", p["name"])
        print("  Version:", p["version"])
        print("  Pfad:", p["path"])
        print()
