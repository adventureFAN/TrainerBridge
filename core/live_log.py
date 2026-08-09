from datetime import datetime
from pathlib import Path


LIVE_LOG_LEVELS = {
    "OK",
    "INFO",
    "WARNING",
    "ERROR"
}


def normalize_live_log_level(level):

    normalized = str(level or "INFO").strip().upper()

    if normalized not in LIVE_LOG_LEVELS:
        return "INFO"

    return normalized


def _home_path_aliases(home=None):

    home_path = Path.home() if home is None else Path(home)
    aliases = {str(home_path)}

    try:
        aliases.add(str(home_path.resolve()))
    except OSError:
        pass

    username = home_path.name

    if (
        username
        and str(home_path.parent) in {"/home", "/var/home"}
    ):
        aliases.add(f"/home/{username}")
        aliases.add(f"/var/home/{username}")

    return sorted(
        (alias.rstrip("/") for alias in aliases if alias),
        key=len,
        reverse=True
    )


def sanitize_live_log_message(message, home=None):
    """Shorten the current user's home path before it reaches the Live Log.

    Bazzite commonly exposes the same home as both ``/home/<user>`` and
    ``/var/home/<user>``.  Normalize either form to ``~`` so a manually copied
    or saved diagnostic log does not disclose the local account name merely
    because TrainerBridge logged a path.
    """

    text = str(message)

    for home_path in _home_path_aliases(home):
        if text == home_path:
            text = "~"
            continue

        text = text.replace(
            f"{home_path}/",
            "~/"
        )

    return text


def format_live_log_entry(
    message,
    level="INFO",
    when=None,
    home=None
):

    if when is None:
        when = datetime.now()

    timestamp = when.strftime("%H:%M:%S")
    normalized_level = normalize_live_log_level(level)
    sanitized_message = sanitize_live_log_message(
        message,
        home=home
    )

    return (
        f"{timestamp}  "
        f"{normalized_level:<7}  "
        f"{sanitized_message}"
    )
