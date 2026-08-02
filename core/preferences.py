import os

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from core.paths import DATA_DIR
from core.version import APP_NAME


THEME_KEY = "appearance/theme"
REMEMBER_WINDOW_GEOMETRY_KEY = "appearance/remember_window_geometry"
LEGACY_THEME_KEY = "general/theme"
LEGACY_REMEMBER_WINDOW_GEOMETRY_KEY = "general/remember_window_geometry"
BACKUP_POLICY_KEY = "backups/policy"
BACKUP_METHOD_KEY = "backups/method"
HIDE_TRAINER_REQUIREMENTS_KEY = "notices/hide_trainer_requirements"
HIDE_EARLY_TRAINER_EXIT_KEY = "notices/hide_early_trainer_exit"

THEME_SYSTEM = "system"
THEME_LIGHT = "light"
THEME_DARK = "dark"

BACKUP_POLICY_ASK = "ask"
BACKUP_POLICY_ALWAYS = "always"
BACKUP_POLICY_NEVER = "never"

BACKUP_METHOD_AUTO = "auto"
BACKUP_METHOD_COMPRESSED = "compressed"
BACKUP_METHOD_FOLDER = "folder"


SETTINGS_FILE = DATA_DIR / "settings.ini"

# Keep one long-lived QSettings instance for the whole application. Creating a
# separate instance for every window can leave several stale in-memory views of
# the same INI file. When those windows save geometry during shutdown, an older
# view can overwrite a theme that was just selected in the Options dialog.
_SETTINGS = None


def _extract_legacy_appearance_values():
    """Remove old duplicated ``[%General]`` sections and keep their last values.

    Older TrainerBridge builds stored appearance settings below ``general/``.
    QSettings escapes that reserved INI section as ``[%General]``. Multiple
    QSettings instances could write duplicate sections with different values.
    The last value is the newest one, so retain it during one-time migration.
    """
    if not SETTINGS_FILE.is_file():
        return {}

    try:
        original = SETTINGS_FILE.read_text(encoding="utf-8")
    except OSError:
        return {}

    captured = {}
    cleaned_lines = []
    in_legacy_section = False
    changed = False

    for line in original.splitlines(keepends=True):
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            # ``[%General]`` is QSettings' escaped representation of the
            # application group named ``general``. Also accept an old literal
            # lowercase ``[general]`` section, but do not remove Qt's reserved
            # top-level ``[General]`` section.
            in_legacy_section = (
                section.casefold() == "%general"
                or section == "general"
            )

            if in_legacy_section:
                changed = True
                continue

            cleaned_lines.append(line)
            continue

        if in_legacy_section:
            if "=" in line:
                key, value = line.split("=", 1)
                normalized_key = key.strip().casefold()
                if normalized_key in {
                    "theme",
                    "remember_window_geometry"
                }:
                    captured[normalized_key] = value.strip()
            continue

        cleaned_lines.append(line)

    if changed:
        temporary_file = SETTINGS_FILE.with_name(
            f".{SETTINGS_FILE.name}.tmp"
        )
        try:
            temporary_file.write_text(
                "".join(cleaned_lines),
                encoding="utf-8"
            )
            os.replace(temporary_file, SETTINGS_FILE)
        except OSError:
            try:
                temporary_file.unlink(missing_ok=True)
            except OSError:
                pass

    return captured


def _valid_theme(value):
    value = str(value or "").lower()
    if value in {THEME_SYSTEM, THEME_LIGHT, THEME_DARK}:
        return value
    return THEME_SYSTEM


def _bool_from_ini(value, default=True):
    if value is None:
        return default

    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def application_settings():
    global _SETTINGS

    if _SETTINGS is not None:
        return _SETTINGS

    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    legacy_file_values = _extract_legacy_appearance_values()
    settings = QSettings(str(SETTINGS_FILE), QSettings.Format.IniFormat)

    if not SETTINGS_FILE.exists() and not settings.allKeys():
        legacy = QSettings(APP_NAME, APP_NAME)
        for key in legacy.allKeys():
            mapped_key = {
                LEGACY_THEME_KEY: THEME_KEY,
                LEGACY_REMEMBER_WINDOW_GEOMETRY_KEY:
                    REMEMBER_WINDOW_GEOMETRY_KEY
            }.get(key, key)
            settings.setValue(mapped_key, legacy.value(key))

    if not settings.contains(THEME_KEY):
        legacy_theme = legacy_file_values.get("theme")
        if legacy_theme is None:
            legacy_theme = settings.value(
                LEGACY_THEME_KEY,
                THEME_SYSTEM
            )
        settings.setValue(THEME_KEY, _valid_theme(legacy_theme))

    if not settings.contains(REMEMBER_WINDOW_GEOMETRY_KEY):
        legacy_geometry = legacy_file_values.get(
            "remember_window_geometry"
        )
        if legacy_geometry is None:
            legacy_geometry = settings.value(
                LEGACY_REMEMBER_WINDOW_GEOMETRY_KEY,
                True
            )
        settings.setValue(
            REMEMBER_WINDOW_GEOMETRY_KEY,
            _bool_from_ini(legacy_geometry, True)
        )

    settings.remove(LEGACY_THEME_KEY)
    settings.remove(LEGACY_REMEMBER_WINDOW_GEOMETRY_KEY)
    settings.sync()

    _SETTINGS = settings
    return _SETTINGS


def remember_window_geometry(settings=None):
    settings = settings or application_settings()
    return settings.value(
        REMEMBER_WINDOW_GEOMETRY_KEY,
        True,
        type=bool
    )


def _remember_system_appearance(application):
    if application.property("trainerbridge_system_style") is None:
        application.setProperty(
            "trainerbridge_system_style",
            application.style().objectName()
        )

    if application.property("trainerbridge_system_palette") is None:
        application.setProperty(
            "trainerbridge_system_palette",
            QPalette(application.palette())
        )


def _restore_system_appearance(application):
    style_name = application.property("trainerbridge_system_style")
    palette = application.property("trainerbridge_system_palette")

    if style_name:
        style = QStyleFactory.create(str(style_name))
        if style is not None:
            application.setStyle(style)

    if isinstance(palette, QPalette):
        application.setPalette(QPalette(palette))
    else:
        application.setPalette(QPalette())

    application.setStyleSheet("")


def _set_color_scheme(application, theme):
    """Tell Qt and the window manager which color scheme is intended.

    Qt versions before setColorScheme support simply ignore this hint.
    """
    try:
        style_hints = application.styleHints()
        setter = getattr(style_hints, "setColorScheme", None)
        color_scheme = getattr(Qt, "ColorScheme", None)

        if setter is None or color_scheme is None:
            return

        if theme == THEME_LIGHT:
            setter(color_scheme.Light)
        elif theme == THEME_DARK:
            setter(color_scheme.Dark)
        else:
            setter(color_scheme.Unknown)
    except (AttributeError, TypeError, RuntimeError):
        pass


def _apply_disabled_colors(palette, text, button_text, window_text):
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        text
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        button_text
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        window_text
    )


def _light_palette():
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(246, 246, 246))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(242, 242, 242))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.Text, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(200, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(0, 92, 180))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(95, 55, 150))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(48, 126, 190))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(248, 248, 248))
    palette.setColor(QPalette.ColorRole.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.ColorRole.Mid, QColor(190, 190, 190))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(105, 105, 105))

    placeholder_role = getattr(QPalette.ColorRole, "PlaceholderText", None)
    if placeholder_role is not None:
        palette.setColor(placeholder_role, QColor(115, 115, 115))

    _apply_disabled_colors(
        palette,
        QColor(145, 145, 145),
        QColor(145, 145, 145),
        QColor(145, 145, 145)
    )

    return palette


def _dark_palette():
    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(235, 235, 235))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(42, 42, 42))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(235, 235, 235))
    palette.setColor(QPalette.ColorRole.Text, QColor(235, 235, 235))
    palette.setColor(QPalette.ColorRole.Button, QColor(55, 55, 55))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(235, 235, 235))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 90, 90))
    palette.setColor(QPalette.ColorRole.Link, QColor(90, 170, 255))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(190, 130, 255))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(55, 120, 190))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Light, QColor(85, 85, 85))
    palette.setColor(QPalette.ColorRole.Midlight, QColor(70, 70, 70))
    palette.setColor(QPalette.ColorRole.Dark, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.Mid, QColor(38, 38, 38))
    palette.setColor(QPalette.ColorRole.Shadow, QColor(12, 12, 12))

    placeholder_role = getattr(QPalette.ColorRole, "PlaceholderText", None)
    if placeholder_role is not None:
        palette.setColor(placeholder_role, QColor(145, 145, 145))

    _apply_disabled_colors(
        palette,
        QColor(135, 135, 135),
        QColor(135, 135, 135),
        QColor(135, 135, 135)
    )

    return palette


def apply_theme(application=None, theme=None):
    application = application or QApplication.instance()
    if application is None:
        return THEME_SYSTEM

    _remember_system_appearance(application)

    settings = application_settings()
    selected_theme = str(
        theme
        if theme is not None
        else settings.value(THEME_KEY, THEME_SYSTEM)
    ).lower()

    if selected_theme not in {
        THEME_SYSTEM,
        THEME_LIGHT,
        THEME_DARK
    }:
        selected_theme = THEME_SYSTEM

    if selected_theme == THEME_SYSTEM:
        _set_color_scheme(application, THEME_SYSTEM)
        _restore_system_appearance(application)

    elif selected_theme == THEME_LIGHT:
        _set_color_scheme(application, THEME_LIGHT)
        style = QStyleFactory.create("Fusion")
        if style is not None:
            application.setStyle(style)
        application.setStyleSheet("")
        application.setPalette(_light_palette())

    else:
        _set_color_scheme(application, THEME_DARK)
        style = QStyleFactory.create("Fusion")
        if style is not None:
            application.setStyle(style)
        application.setStyleSheet("")
        application.setPalette(_dark_palette())

    # Applying a theme must not write settings. The Options dialog owns the
    # persisted selection; startup only reads and applies it.
    return selected_theme
