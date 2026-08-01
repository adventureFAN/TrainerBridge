from core.storage import load_trainers
from pathlib import Path


def apply_trainer_info(game):

    trainers = load_trainers()

    data = trainers.get(str(game.appid))

    if not data:
        return game

    trainer = Path(
        data["trainer"]
    )

    if trainer.exists():
        game.trainer_path = trainer

    return game
