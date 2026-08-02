from dataclasses import dataclass
from pathlib import Path


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
