import shutil
from pathlib import Path


APP_NAME = "TrainerBridge"

DATA_DIR = (
    Path.home()
    / ".local"
    / "share"
    / APP_NAME
)

LEGACY_DATA_DIR = (
    Path.home()
    / ".local"
    / "share"
    / "proton-trainer-manager"
)

CACHE_DIR = DATA_DIR / "cache"
TRAINER_DIR = DATA_DIR / "trainers"
CONFIG_FILE = DATA_DIR / "trainers.json"


def _copy_missing_files(source, target):

    for source_path in source.rglob("*"):

        relative_path = source_path.relative_to(source)
        target_path = target / relative_path

        if source_path.is_dir():

            target_path.mkdir(
                parents=True,
                exist_ok=True
            )

            continue

        if target_path.exists():
            continue

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source_path,
            target_path
        )


def migrate_legacy_data():

    if (
        LEGACY_DATA_DIR.exists()
        and
        not DATA_DIR.exists()
    ):

        try:

            LEGACY_DATA_DIR.rename(
                DATA_DIR
            )

        except OSError:

            DATA_DIR.mkdir(
                parents=True,
                exist_ok=True
            )

            _copy_missing_files(
                LEGACY_DATA_DIR,
                DATA_DIR
            )

    elif (
        LEGACY_DATA_DIR.exists()
        and
        DATA_DIR.exists()
    ):

        _copy_missing_files(
            LEGACY_DATA_DIR,
            DATA_DIR
        )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    TRAINER_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


migrate_legacy_data()
