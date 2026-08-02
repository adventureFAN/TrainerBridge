import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from core.host_process import host_environment


def _host_opener():
    candidates = (
        ("/usr/bin/xdg-open",),
        ("/usr/bin/gio", "open"),
    )

    for command in candidates:
        if Path(command[0]).is_file():
            return command

    xdg_open = shutil.which("xdg-open")
    if xdg_open:
        return (xdg_open,)

    gio = shutil.which("gio")
    if gio:
        return (gio, "open")

    return None


def open_local_path(path):
    path = Path(path).expanduser().resolve()
    command = _host_opener()

    if command:
        try:
            subprocess.Popen(
                [*command, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=host_environment(),
            )
            return True
        except OSError:
            pass

    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def open_url(url):
    command = _host_opener()

    if command:
        try:
            subprocess.Popen(
                [*command, str(url)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
                env=host_environment(),
            )
            return True
        except OSError:
            pass

    return QDesktopServices.openUrl(QUrl(str(url)))
