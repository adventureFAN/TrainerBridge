import os


PYINSTALLER_ENVIRONMENT_KEYS = (
    "PYTHONHOME",
    "PYTHONPATH",
    "PYINSTALLER_RESET_ENVIRONMENT"
)

QT_ENVIRONMENT_KEYS = (
    "QT_PLUGIN_PATH",
    "QML2_IMPORT_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH"
)


def host_environment(base_environment=None):
    """Return an environment suitable for host-system programs.

    Frozen applications can modify library and Qt search paths. Steam,
    Proton, Flatpak and Protontricks must use the host system's libraries,
    not the copies bundled with TrainerBridge.
    """

    environment = dict(
        os.environ
        if base_environment is None
        else base_environment
    )

    original_library_path = environment.get(
        "LD_LIBRARY_PATH_ORIG"
    )

    if original_library_path is None:

        environment.pop(
            "LD_LIBRARY_PATH",
            None
        )

    else:

        environment[
            "LD_LIBRARY_PATH"
        ] = original_library_path

    for key in PYINSTALLER_ENVIRONMENT_KEYS:

        environment.pop(
            key,
            None
        )

    for key in QT_ENVIRONMENT_KEYS:

        environment.pop(
            key,
            None
        )

    return environment
