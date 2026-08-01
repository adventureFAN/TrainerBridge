import argparse
import sys

from core.protontricks import (
    ProtontricksManager,
    WINDOWS_VERSION_LABELS
)


DEFAULT_APPID = "3489700"


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Show the current Windows compatibility "
            "version of a Proton prefix."
        )
    )

    parser.add_argument(
        "--appid",
        default=DEFAULT_APPID,
        help=(
            "Steam AppID "
            f"(default: {DEFAULT_APPID})"
        )
    )

    arguments = parser.parse_args()

    manager = ProtontricksManager.detect()

    if not manager:

        print("Protontricks was not found.")
        return 1

    try:

        version = manager.get_windows_version(
            arguments.appid
        )

    except Exception as error:

        print(
            f"Could not detect the Windows version: {error}"
        )

        return 1

    label = WINDOWS_VERSION_LABELS.get(
        version,
        version
    )

    print(
        f"AppID {arguments.appid}: {label} ({version})"
    )

    return 0


if __name__ == "__main__":

    sys.exit(
        main()
    )
