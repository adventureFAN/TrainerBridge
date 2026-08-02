from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

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


def application_settings():
    return QSettings(APP_NAME, APP_NAME)


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


def _light_palette(application):
    style = QStyleFactory.create("Fusion")
    if style is not None:
        application.setStyle(style)
        return style.standardPalette()

    return QPalette()


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
    palette.setColor(QPalette.ColorRole.Highlight, QColor(55, 120, 190))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(135, 135, 135))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(135, 135, 135))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(135, 135, 135))

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
        _restore_system_appearance(application)

    elif selected_theme == THEME_LIGHT:
        application.setStyleSheet("")
        application.setPalette(_light_palette(application))

    else:
        style = QStyleFactory.create("Fusion")
        if style is not None:
            application.setStyle(style)
        application.setStyleSheet("")
        application.setPalette(_dark_palette())

    settings.setValue(THEME_KEY, selected_theme)
    return selected_theme
