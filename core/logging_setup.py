import logging


def setup_logging():
    """Keep Python logging quiet without creating persistent log files.

    TrainerBridge's user-facing diagnostics live in the in-app Live Log. The
    terminal remains available for direct ``print`` output from low-level launch
    helpers, but normal application startup must not create a disk log merely
    because the program was opened.
    """

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
    root_logger.addHandler(logging.NullHandler())

    return None
