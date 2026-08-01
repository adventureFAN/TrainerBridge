import logging
import sys
from datetime import datetime

from core.paths import LOG_DIR
from core.version import APP_NAME, APP_VERSION


class LoggingStream:

    def __init__(
        self,
        logger,
        level,
        original_stream=None
    ):

        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self.buffer = ""


    def write(self, text):

        if not text:
            return 0

        if self.original_stream:

            try:

                self.original_stream.write(
                    text
                )

            except Exception:

                pass

        self.buffer += text

        while "\n" in self.buffer:

            line, self.buffer = self.buffer.split(
                "\n",
                1
            )

            if line.strip():

                self.logger.log(
                    self.level,
                    line.rstrip()
                )

        return len(text)


    def flush(self):

        if self.buffer.strip():

            self.logger.log(
                self.level,
                self.buffer.rstrip()
            )

        self.buffer = ""

        if self.original_stream:

            try:

                self.original_stream.flush()

            except Exception:

                pass


    def isatty(self):

        if not self.original_stream:
            return False

        try:

            return self.original_stream.isatty()

        except Exception:

            return False


def setup_logging():

    LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    log_file = LOG_DIR / (
        f"trainerbridge-{timestamp}.log"
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    root_logger.handlers.clear()

    file_handler = logging.FileHandler(
        log_file,
        encoding="utf-8"
    )

    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        )
    )

    root_logger.addHandler(
        file_handler
    )

    logger = logging.getLogger(
        APP_NAME
    )

    logger.info(
        "%s %s starting",
        APP_NAME,
        APP_VERSION
    )

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = LoggingStream(
        logger,
        logging.INFO,
        original_stdout
    )

    sys.stderr = LoggingStream(
        logger,
        logging.ERROR,
        original_stderr
    )

    return log_file
