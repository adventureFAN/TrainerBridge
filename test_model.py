from pathlib import Path
from core.models import GameProfile


game = GameProfile(
    name="Metaphor: ReFantazio",
    appid="2679460",
    library=Path("/test")
)

print(game)
