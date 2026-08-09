import re
from pathlib import Path


_STEAM_APPID_PATTERN = re.compile(r"[0-9]+\Z")


def validate_steam_appid(appid):
    """Return a normalized Steam AppID or reject unsafe/unexpected input."""

    value = str(appid)

    if not _STEAM_APPID_PATTERN.fullmatch(value):
        raise ValueError("Steam AppID must contain ASCII digits only.")

    return value


def validate_steam_install_dir(install_dir):
    """Validate Steam's manifest ``installdir`` as one relative directory name."""

    value = str(install_dir)

    if not value or "\x00" in value:
        raise ValueError("Steam installdir must be a non-empty directory name.")

    relative_path = Path(value)

    if (
        relative_path.is_absolute()
        or len(relative_path.parts) != 1
        or relative_path.parts[0] in {".", ".."}
    ):
        raise ValueError(
            "Steam installdir must be a single relative directory name."
        )

    return value


def build_steam_game_path(library, install_dir):
    """Build a safe ``steamapps/common/<installdir>`` path from manifest data."""

    validated_install_dir = validate_steam_install_dir(install_dir)

    return (
        Path(library)
        / "steamapps"
        / "common"
        / validated_install_dir
    )
