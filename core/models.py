from dataclasses import dataclass
from pathlib import Path

from core.validation import validate_steam_appid


@dataclass
class GameProfile:

    name: str
    appid: str
    library: Path

    prefix: Path | None = None
    game_path: Path | None = None

    proton_name: str | None = None
    proton_version: str | None = None
    proton_path: Path | None = None

    trainer_path: Path | None = None

    status: str = "UNKNOWN"

    def __post_init__(self):
        self.appid = validate_steam_appid(self.appid)
