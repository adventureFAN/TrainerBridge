import json
import shutil
from pathlib import Path


CONFIG_DIR = Path.home() / ".local/share/proton-trainer-manager"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = CONFIG_DIR / "trainers.json"

TRAINER_DIR = CONFIG_DIR / "trainers"
TRAINER_DIR.mkdir(parents=True, exist_ok=True)


def load_trainers():

    if not CONFIG_FILE.exists():
        return {}

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_trainers(data):

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def import_trainer(appid, trainer_file):

    trainer_file = Path(trainer_file)

    if not trainer_file.exists():
        raise FileNotFoundError(
            f"Trainer nicht gefunden: {trainer_file}"
        )

    target_dir = TRAINER_DIR / str(appid)
    target_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    target_file = target_dir / trainer_file.name

    shutil.copy2(
        trainer_file,
        target_file
    )

    trainers = load_trainers()

    trainers[str(appid)] = {
        "trainer": str(target_file)
    }

    save_trainers(trainers)

    return target_file
