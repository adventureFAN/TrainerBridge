import sys
from pathlib import Path


def resource_path(relative_path):

    if getattr(sys, "frozen", False):

        base_path = Path(
            getattr(sys, "_MEIPASS")
        )

    else:

        base_path = (
            Path(__file__)
            .resolve()
            .parents[1]
        )

    return base_path / relative_path
