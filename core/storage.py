import json
import shutil
from pathlib import Path

from core.paths import (
    CONFIG_FILE,
    DATA_DIR,
    LEGACY_DATA_DIR,
    TRAINER_DIR
)
from core.validation import validate_steam_appid


def _migrate_saved_trainer_paths(data):

    changed = False

    for appid, trainer_data in data.items():

        del appid

        if not isinstance(trainer_data, dict):
            continue

        trainer_value = trainer_data.get(
            "trainer"
        )

        if not trainer_value:
            continue

        trainer_path = Path(
            trainer_value
        )

        try:

            relative_path = trainer_path.relative_to(
                LEGACY_DATA_DIR
            )

        except ValueError:

            continue

        new_path = (
            DATA_DIR
            / relative_path
        )

        trainer_data["trainer"] = str(
            new_path
        )

        changed = True

    return changed


def load_trainers():

    if not CONFIG_FILE.exists():
        return {}

    try:

        with open(
            CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except (
        OSError,
        json.JSONDecodeError
    ):

        return {}

    if not isinstance(data, dict):
        return {}

    if _migrate_saved_trainer_paths(data):

        save_trainers(
            data
        )

    return data


def save_trainers(data):

    CONFIG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temporary_file = CONFIG_FILE.with_suffix(
        ".tmp"
    )

    with open(
        temporary_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )

    temporary_file.replace(
        CONFIG_FILE
    )


def import_trainer(appid, trainer_file):

    appid = validate_steam_appid(appid)

    trainer_file = Path(
        trainer_file
    )

    if not trainer_file.exists():

        raise FileNotFoundError(
            f"Trainer file not found: {trainer_file}"
        )

    if not trainer_file.is_file():

        raise ValueError(
            f"Trainer path is not a file: {trainer_file}"
        )

    target_dir = (
        TRAINER_DIR
        / appid
    )

    target_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    target_file = (
        target_dir
        / trainer_file.name
    )

    if trainer_file.resolve() != target_file.resolve():
        temporary_file = target_dir / f".{trainer_file.name}.importing"

        shutil.copy2(
            trainer_file,
            temporary_file
        )

        temporary_file.replace(
            target_file
        )

    for existing_file in target_dir.iterdir():
        if existing_file == target_file:
            continue

        if existing_file.is_dir():
            shutil.rmtree(existing_file)
        else:
            existing_file.unlink()

    trainers = load_trainers()

    trainers[appid] = {
        "trainer": str(target_file)
    }

    save_trainers(
        trainers
    )

    return target_file


def remove_trainer(appid):

    appid = validate_steam_appid(appid)

    trainers = load_trainers()
    trainer_data = trainers.pop(appid, None)

    target_dir = TRAINER_DIR / appid

    if target_dir.exists():
        shutil.rmtree(target_dir)

    if trainer_data is not None:
        save_trainers(trainers)
        return True

    return False
