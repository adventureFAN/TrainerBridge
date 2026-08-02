from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

from core.paths import DATA_DIR
from core.version import APP_NAME


THEME_KEY = "general/theme"
REMEMBER_WINDOW_GEOMETRY_KEY = "general/remember_window_geometry"
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


def application_settings():
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    settings = QSettings(str(SETTINGS_FILE), QSettings.Format.IniFormat)

    if not SETTINGS_FILE.exists() and not settings.allKeys():
        legacy = QSettings(APP_NAME, APP_NAME)
        for key in legacy.allKeys():
            settings.setValue(key, legacy.value(key))
        settings.sync()

    return settings


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

    settings.setValue(THEME_KEY, selected_theme)
    settings.sync()
    return selected_theme
