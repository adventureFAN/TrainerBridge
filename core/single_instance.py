import fcntl
import os
from pathlib import Path

from core.paths import DATA_DIR


LOCK_PATH = DATA_DIR / ".trainerbridge.lock"


class SingleInstanceLock:

    def __init__(
        self,
        path=None
    ):

        self.path = Path(
            path
            if path is not None
            else LOCK_PATH
        )

        self._file_descriptor = None


    @property
    def acquired(self):

        return self._file_descriptor is not None


    def acquire(self):

        if self.acquired:
            return True

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        flags = (
            os.O_RDWR
            | os.O_CREAT
        )

        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC

        file_descriptor = os.open(
            self.path,
            flags,
            0o600
        )

        try:

            fcntl.flock(
                file_descriptor,
                fcntl.LOCK_EX
                | fcntl.LOCK_NB
            )

        except BlockingIOError:

            os.close(
                file_descriptor
            )

            return False

        try:

            os.fchmod(
                file_descriptor,
                0o600
            )

        except OSError:

            pass

        os.ftruncate(
            file_descriptor,
            0
        )

        os.write(
            file_descriptor,
            str(os.getpid()).encode(
                "ascii"
            )
        )

        self._file_descriptor = (
            file_descriptor
        )

        return True


    def release(self):

        if not self.acquired:
            return

        file_descriptor = (
            self._file_descriptor
        )

        self._file_descriptor = None

        try:

            fcntl.flock(
                file_descriptor,
                fcntl.LOCK_UN
            )

        finally:

            os.close(
                file_descriptor
            )


    def __enter__(self):

        if not self.acquire():

            raise RuntimeError(
                "Another TrainerBridge instance is already running."
            )

        return self


    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ):

        self.release()
