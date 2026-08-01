import argparse
import sys

from core.protontricks import (
    ProtontricksCommandError,
    ProtontricksError,
    ProtontricksManager,
    SUPPORTED_CATEGORIES
)

from core.scanner import scan_all_games


DEFAULT_APPID = "3489700"

DEFAULT_SEARCH = "dotnet48"


def find_game(
    games,
    appid
):

    for game in games:

        if game.appid == appid:

            return game


    return None


def print_component(
    component
):

    installed_text = (
        "INSTALLIERT"
        if component.installed
        else "nicht installiert"
    )


    print(
        f"- {component.name}"
    )

    print(
        f"  Kategorie: "
        f"{SUPPORTED_CATEGORIES.get(
            component.category,
            component.category
        )}"
    )

    print(
        f"  Status: {installed_text}"
    )

    print(
        f"  Beschreibung: "
        f"{component.description}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "TrainerBridge Protontricks-Test"
        )
    )


    parser.add_argument(
        "--appid",
        default=DEFAULT_APPID,
        help=(
            "Steam-AppID des Spiels "
            f"(Standard: {DEFAULT_APPID})"
        )
    )


    parser.add_argument(
        "--search",
        default=DEFAULT_SEARCH,
        help=(
            "Komponente, nach der gesucht wird "
            f"(Standard: {DEFAULT_SEARCH})"
        )
    )


    parser.add_argument(
        "--install",
        metavar="KOMPONENTE",
        help=(
            "Installiert nach ausdrücklicher "
            "Bestätigung eine Komponente"
        )
    )


    arguments = parser.parse_args()


    appid = str(
        arguments.appid
    )


    print(
        "=== TrainerBridge Protontricks-Test ==="
    )

    print()

    print(
        "Scanne Steam-Spiele..."
    )


    games = scan_all_games()

    game = find_game(
        games,
        appid
    )


    if not game:

        print()
        print(
            f"Kein Steam-Spiel mit "
            f"AppID {appid} gefunden."
        )

        return 1


    print()
    print("Spiel:")
    print(game.name)

    print()
    print("AppID:")
    print(game.appid)

    print()
    print("Library:")
    print(game.library)

    print()
    print("Prefix:")
    print(game.prefix)

    print()
    print("Proton:")
    print(game.proton_path)


    if not game.prefix:

        print()
        print(
            "Für dieses Spiel wurde noch "
            "kein Proton-Prefix gefunden."
        )

        print(
            "Starte das Spiel mindestens "
            "einmal über Steam."
        )

        return 1


    manager = (
        ProtontricksManager.detect()
    )


    if not manager:

        print()
        print(
            "Protontricks wurde nicht gefunden."
        )

        print(
            "Weder eine Systeminstallation "
            "noch die Flatpak-Version ist vorhanden."
        )

        return 1


    print()
    print("Protontricks erkannt:")

    print(
        manager.installation.display_name
    )

    print()
    print("Startbefehl:")

    print(
        " ".join(
            manager.installation.command_prefix
        )
    )


    try:

        version = manager.get_version()

    except ProtontricksError as error:

        print()
        print(
            "Version konnte nicht gelesen werden:"
        )

        print(error)

        return 1


    print()
    print("Version:")
    print(version)


    print()
    print(
        "Lese verfügbare Komponenten..."
    )


    try:

        components = (
            manager.list_components(
                appid
            )
        )

    except ProtontricksCommandError as error:

        print()
        print(
            "Komponenten konnten nicht "
            "gelesen werden."
        )

        print()
        print(error)

        if (
            manager.installation.kind
            ==
            "flatpak"
        ):

            print()
            print(
                "Hinweis:"
            )

            print(
                "Bei zusätzlichen Steam-Libraries "
                "benötigt Protontricks als Flatpak "
                "möglicherweise eine passende "
                "Dateisystemberechtigung."
            )

        return 1


    print()
    print(
        f"{len(components)} Komponenten "
        "gefunden."
    )


    for category, category_title in (
        SUPPORTED_CATEGORIES.items()
    ):

        count = sum(
            1
            for component in components
            if component.category == category
        )

        print(
            f"- {category_title}: {count}"
        )


    installed_components = [
        component
        for component in components
        if component.installed
    ]


    print()
    print(
        "Bereits installierte Komponenten:"
    )


    if installed_components:

        for component in (
            installed_components
        ):

            print(
                f"- {component.name}"
            )

    else:

        print(
            "Keine durch Winetricks "
            "protokollierte Komponente."
        )


    search_text = (
        arguments.search
        .strip()
        .lower()
    )


    matches = [
        component
        for component in components
        if (
            search_text
            in component.name.lower()
            or
            search_text
            in component.description.lower()
        )
    ]


    print()
    print(
        f"Suchergebnisse für "
        f"„{arguments.search}“:"
    )


    if matches:

        for component in matches:

            print()
            print_component(
                component
            )

    else:

        print(
            "Keine passende Komponente gefunden."
        )


    if not arguments.install:

        print()
        print(
            "Es wurde nichts installiert."
        )

        print()
        print(
            "Zum Installieren zum Beispiel:"
        )

        print(
            "python test_protontricks.py "
            "--install dotnet48"
        )

        return 0


    install_name = (
        arguments.install
        .strip()
        .lower()
    )


    selected_component = None


    for component in components:

        if (
            component.name.lower()
            ==
            install_name
        ):

            selected_component = component

            break


    if not selected_component:

        print()
        print(
            f"Die Komponente "
            f"„{arguments.install}“ "
            "wurde nicht in der Liste gefunden."
        )

        return 1


    if selected_component.installed:

        print()
        print(
            f"{selected_component.name} "
            "ist laut Winetricks bereits installiert."
        )

        return 0


    if manager.game_is_running(
        appid
    ):

        print()
        print(
            "Das Spiel läuft noch."
        )

        print(
            "Beende Spiel und Trainer "
            "vor der Installation."
        )

        return 1


    print()
    print(
        "ACHTUNG:"
    )

    print(
        f"{selected_component.name} wird "
        f"in den Proton-Prefix von "
        f"{game.name} installiert."
    )

    print()

    print(
        "Dadurch wird der Prefix verändert."
    )

    print(
        "Spiel und Trainer müssen "
        "vollständig geschlossen sein."
    )

    print()

    confirmation = input(
        "Tippe INSTALLIEREN zum Fortfahren: "
    )


    if confirmation != "INSTALLIEREN":

        print()
        print(
            "Installation abgebrochen."
        )

        return 0


    print()
    print(
        f"Installiere "
        f"{selected_component.name}..."
    )

    print(
        "Installerfenster und Meldungen "
        "von Winetricks können erscheinen."
    )

    print()


    try:

        manager.install_component(
            appid,
            selected_component.name
        )

    except ProtontricksError as error:

        print()
        print(
            "Installation fehlgeschlagen:"
        )

        print(error)

        return 1


    print()
    print(
        "Protontricks wurde erfolgreich beendet."
    )


    try:

        installed_afterwards = (
            manager.list_installed(
                appid
            )
        )

    except ProtontricksError:

        installed_afterwards = set()


    if (
        selected_component.name
        in installed_afterwards
    ):

        print()
        print(
            f"{selected_component.name} "
            "wird jetzt als installiert erkannt."
        )

    else:

        print()
        print(
            "Die Komponente wurde nach dem "
            "Protontricks-Durchlauf nicht in "
            "list-installed gefunden."
        )

        print(
            "Das muss nicht zwingend bedeuten, "
            "dass der Installer fehlgeschlagen ist."
        )


    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
