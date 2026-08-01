from dataclasses import dataclass
from pathlib import Path
import shutil

import vdf


STEAM_FLATPAK_APP_ID = "com.valvesoftware.Steam"


@dataclass(
    frozen=True
)
class SteamInstallation:

    kind: str
    display_name: str
    install_path: Path
    config_path: Path | None
    launch_prefix: tuple


def _find_library_config(
    install_path
):

    candidates = [
        install_path
        / "steamapps"
        / "libraryfolders.vdf",
        install_path
        / "config"
        / "libraryfolders.vdf"
    ]

    for candidate in candidates:

        if candidate.exists():
            return candidate

    return None


def _has_steam_data(
    install_path
):

    steamapps = (
        install_path
        / "steamapps"
    )

    if not steamapps.exists():
        return False

    if _find_library_config(
        install_path
    ):
        return True

    return any(
        steamapps.glob(
            "appmanifest_*.acf"
        )
    )


def _manifest_count(
    install_path
):

    steamapps = (
        install_path
        / "steamapps"
    )

    if not steamapps.exists():
        return 0

    return sum(
        1
        for _ in steamapps.glob(
            "appmanifest_*.acf"
        )
    )


def _path_identity(
    path
):

    try:

        return path.resolve()

    except OSError:

        return path.absolute()


def detect_steam_installations():

    home = Path.home()

    steam_command = shutil.which(
        "steam"
    )

    snap_command = shutil.which(
        "snap"
    )

    flatpak_command = shutil.which(
        "flatpak"
    )

    candidates = []

    native_roots = [
        home / ".steam/steam",
        home / ".local/share/Steam",
        home / ".steam/debian-installation"
    ]

    for install_path in native_roots:

        candidates.append(
            SteamInstallation(
                kind="native",
                display_name="Native Steam",
                install_path=install_path,
                config_path=_find_library_config(
                    install_path
                ),
                launch_prefix=(
                    steam_command,
                ) if steam_command else tuple()
            )
        )

    snap_roots = [
        home
        / "snap"
        / "steam"
        / "common"
        / ".local"
        / "share"
        / "Steam",
        home
        / ".snap"
        / "data"
        / "steam"
        / "common"
        / ".local"
        / "share"
        / "Steam"
    ]

    for install_path in snap_roots:

        candidates.append(
            SteamInstallation(
                kind="snap",
                display_name="Steam Snap",
                install_path=install_path,
                config_path=_find_library_config(
                    install_path
                ),
                launch_prefix=(
                    snap_command,
                    "run",
                    "steam"
                ) if snap_command else tuple()
            )
        )

    flatpak_root = (
        home
        / ".var"
        / "app"
        / STEAM_FLATPAK_APP_ID
        / ".local"
        / "share"
        / "Steam"
    )

    candidates.append(
        SteamInstallation(
            kind="flatpak",
            display_name="Steam Flatpak",
            install_path=flatpak_root,
            config_path=_find_library_config(
                flatpak_root
            ),
            launch_prefix=(
                flatpak_command,
                "run",
                STEAM_FLATPAK_APP_ID
            ) if flatpak_command else tuple()
        )
    )

    installations = []
    seen_paths = set()

    for candidate in candidates:

        if not _has_steam_data(
            candidate.install_path
        ):
            continue

        identity = _path_identity(
            candidate.install_path
        )

        if identity in seen_paths:
            continue

        seen_paths.add(
            identity
        )

        installations.append(
            candidate
        )

    installations.sort(
        key=lambda installation: (
            _manifest_count(
                installation.install_path
            ),
            installation.config_path is not None
        ),
        reverse=True
    )

    return installations


def find_steam_installation():

    installations = (
        detect_steam_installations()
    )

    if not installations:
        return None

    return installations[0]


def find_steam_config():

    installation = (
        find_steam_installation()
    )

    if not installation:
        return None

    return installation.config_path


def find_steam_install():

    installation = (
        find_steam_installation()
    )

    if not installation:
        return None

    return installation.install_path


def _append_library(
    libraries,
    seen_paths,
    path
):

    path = Path(
        path
    ).expanduser()

    identity = _path_identity(
        path
    )

    if identity in seen_paths:
        return

    seen_paths.add(
        identity
    )

    libraries.append(
        path
    )


def get_steam_libraries(
    installation=None
):

    if installation is None:

        installation = (
            find_steam_installation()
        )

    if not installation:
        return []

    libraries = []
    seen_paths = set()

    _append_library(
        libraries,
        seen_paths,
        installation.install_path
    )

    config = installation.config_path

    if not config:
        return libraries

    try:

        with open(
            config,
            "r",
            encoding="utf-8"
        ) as file:

            data = vdf.load(
                file
            )

    except (
        OSError,
        UnicodeDecodeError,
        ValueError,
        KeyError,
        TypeError
    ):

        return libraries

    libraryfolders = data.get(
        "libraryfolders",
        {}
    )

    if not isinstance(
        libraryfolders,
        dict
    ):
        return libraries

    for value in libraryfolders.values():

        if not isinstance(
            value,
            dict
        ):
            continue

        library_path = value.get(
            "path"
        )

        if not library_path:
            continue

        _append_library(
            libraries,
            seen_paths,
            library_path
        )

    return libraries


def get_steam_info():

    installation = (
        find_steam_installation()
    )

    if not installation:

        return {
            "kind": None,
            "display_name": None,
            "install_path": None,
            "config_path": None,
            "launch_prefix": tuple(),
            "libraries": []
        }

    return {
        "kind": installation.kind,
        "display_name": installation.display_name,
        "install_path": installation.install_path,
        "config_path": installation.config_path,
        "launch_prefix": installation.launch_prefix,
        "libraries": get_steam_libraries(
            installation
        )
    }
