from PySide6.QtCore import QSettings, Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget
)

from core.paths import BACKUP_DIR, DATA_DIR, TRAINER_DIR
from core.preferences import (
    BACKUP_METHOD_AUTO,
    BACKUP_METHOD_COMPRESSED,
    BACKUP_METHOD_FOLDER,
    BACKUP_METHOD_KEY,
    BACKUP_POLICY_ALWAYS,
    BACKUP_POLICY_ASK,
    BACKUP_POLICY_KEY,
    BACKUP_POLICY_NEVER,
    HIDE_EARLY_TRAINER_EXIT_KEY,
    HIDE_TRAINER_REQUIREMENTS_KEY,
    REMEMBER_WINDOW_GEOMETRY_KEY,
    THEME_DARK,
    THEME_KEY,
    THEME_LIGHT,
    THEME_SYSTEM,
    apply_theme,
    remember_window_geometry
)
from core.version import APP_NAME


OPTIONS_GEOMETRY_KEY = "options/geometry"


class OptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings(APP_NAME, APP_NAME)
        self.setWindowTitle(f"Options - {APP_NAME}")
        self.resize(620, 460)
        self.setMinimumSize(560, 420)

        self._build_interface()
        self._load_settings()
        self._restore_geometry()

    def _build_interface(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()

        self.tabs.addTab(self._build_general_tab(), "General")
        self.tabs.addTab(self._build_backups_tab(), "Backups")
        self.tabs.addTab(self._build_messages_tab(), "Messages")

        layout.addWidget(self.tabs, 1)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self._accept_changes)
        self.button_box.rejected.connect(self.reject)

        apply_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Apply
        )
        apply_button.clicked.connect(self._save_settings)

        layout.addWidget(self.button_box)

    def _build_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("System", THEME_SYSTEM)
        self.theme_combo.addItem("Light", THEME_LIGHT)
        self.theme_combo.addItem("Dark", THEME_DARK)
        appearance_layout.addRow("Theme:", self.theme_combo)

        self.remember_geometry_checkbox = QCheckBox(
            "Remember window sizes and positions"
        )
        appearance_layout.addRow("", self.remember_geometry_checkbox)

        storage_group = QGroupBox("Storage")
        storage_layout = QFormLayout(storage_group)

        data_path = QLabel(str(DATA_DIR))
        data_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        data_path.setWordWrap(True)

        trainer_path = QLabel(str(TRAINER_DIR))
        trainer_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        trainer_path.setWordWrap(True)

        storage_layout.addRow("Data folder:", data_path)
        storage_layout.addRow("Trainer folder:", trainer_path)

        note = QLabel(
            "Storage paths are fixed for version 1.0 to keep migration and "
            "recovery predictable."
        )
        note.setWordWrap(True)
        storage_layout.addRow("", note)

        layout.addWidget(appearance_group)
        layout.addWidget(storage_group)
        layout.addStretch(1)
        return widget

    def _build_backups_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        behavior_group = QGroupBox("Before installing components")
        behavior_layout = QFormLayout(behavior_group)

        self.backup_policy_combo = QComboBox()
        self.backup_policy_combo.addItem("Ask every time", BACKUP_POLICY_ASK)
        self.backup_policy_combo.addItem(
            "Always create a safety backup",
            BACKUP_POLICY_ALWAYS
        )
        self.backup_policy_combo.addItem(
            "Never create a safety backup",
            BACKUP_POLICY_NEVER
        )
        behavior_layout.addRow("Backup behavior:", self.backup_policy_combo)

        self.backup_method_combo = QComboBox()
        self.backup_method_combo.addItem(
            "Automatic (recommended)",
            BACKUP_METHOD_AUTO
        )
        self.backup_method_combo.addItem(
            "Always use compressed archive",
            BACKUP_METHOD_COMPRESSED
        )
        self.backup_method_combo.addItem(
            "Always use folder copy",
            BACKUP_METHOD_FOLDER
        )
        behavior_layout.addRow("Storage method:", self.backup_method_combo)

        method_help = QLabel(
            "Automatic uses a fast copy-on-write folder backup when supported "
            "and a compressed archive otherwise. Exactly one safety backup is "
            "kept per game."
        )
        method_help.setWordWrap(True)
        behavior_layout.addRow("", method_help)

        location_group = QGroupBox("Backup location")
        location_layout = QHBoxLayout(location_group)

        location_label = QLabel(str(BACKUP_DIR))
        location_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        location_label.setWordWrap(True)

        open_button = QPushButton("Open Backup Folder")
        open_button.clicked.connect(self._open_backup_folder)

        location_layout.addWidget(location_label, 1)
        location_layout.addWidget(open_button)

        layout.addWidget(behavior_group)
        layout.addWidget(location_group)
        layout.addStretch(1)
        return widget

    def _build_messages_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        messages_group = QGroupBox("Optional notices")
        messages_layout = QVBoxLayout(messages_group)

        self.requirements_notice_checkbox = QCheckBox(
            "Show the trainer requirements notice"
        )
        self.early_exit_notice_checkbox = QCheckBox(
            "Show the early trainer exit and runtime hint"
        )

        messages_layout.addWidget(self.requirements_notice_checkbox)
        messages_layout.addWidget(self.early_exit_notice_checkbox)

        reset_button = QPushButton("Reset all hidden messages")
        reset_button.clicked.connect(self._reset_hidden_messages)

        layout.addWidget(messages_group)
        layout.addWidget(reset_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
        return widget

    def _load_settings(self):
        theme = str(self.settings.value(THEME_KEY, THEME_SYSTEM))
        theme_index = self.theme_combo.findData(theme)
        self.theme_combo.setCurrentIndex(max(0, theme_index))

        self.remember_geometry_checkbox.setChecked(
            self.settings.value(
                REMEMBER_WINDOW_GEOMETRY_KEY,
                True,
                type=bool
            )
        )

        backup_policy = str(
            self.settings.value(BACKUP_POLICY_KEY, BACKUP_POLICY_ASK)
        )
        policy_index = self.backup_policy_combo.findData(backup_policy)
        self.backup_policy_combo.setCurrentIndex(max(0, policy_index))

        backup_method = str(
            self.settings.value(BACKUP_METHOD_KEY, BACKUP_METHOD_AUTO)
        )
        method_index = self.backup_method_combo.findData(backup_method)
        self.backup_method_combo.setCurrentIndex(max(0, method_index))

        self.requirements_notice_checkbox.setChecked(
            not self.settings.value(
                HIDE_TRAINER_REQUIREMENTS_KEY,
                False,
                type=bool
            )
        )
        self.early_exit_notice_checkbox.setChecked(
            not self.settings.value(
                HIDE_EARLY_TRAINER_EXIT_KEY,
                False,
                type=bool
            )
        )

    def _save_settings(self):
        self.settings.setValue(THEME_KEY, self.theme_combo.currentData())
        remember_geometry = self.remember_geometry_checkbox.isChecked()

        self.settings.setValue(
            REMEMBER_WINDOW_GEOMETRY_KEY,
            remember_geometry
        )

        if not remember_geometry:
            for key in (
                "main/geometry",
                "main/window_state",
                "main/splitter_sizes",
                "components/geometry",
                "about/geometry",
                OPTIONS_GEOMETRY_KEY
            ):
                self.settings.remove(key)
        self.settings.setValue(
            BACKUP_POLICY_KEY,
            self.backup_policy_combo.currentData()
        )
        self.settings.setValue(
            BACKUP_METHOD_KEY,
            self.backup_method_combo.currentData()
        )
        self.settings.setValue(
            HIDE_TRAINER_REQUIREMENTS_KEY,
            not self.requirements_notice_checkbox.isChecked()
        )
        self.settings.setValue(
            HIDE_EARLY_TRAINER_EXIT_KEY,
            not self.early_exit_notice_checkbox.isChecked()
        )
        self.settings.sync()

        apply_theme(theme=self.theme_combo.currentData())

    def _accept_changes(self):
        self._save_settings()
        self.accept()

    def _reset_hidden_messages(self):
        self.requirements_notice_checkbox.setChecked(True)
        self.early_exit_notice_checkbox.setChecked(True)

        QMessageBox.information(
            self,
            "Messages reset",
            "All optional notices are enabled again."
        )

    def _open_backup_folder(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(BACKUP_DIR)))

    def _restore_geometry(self):
        if not remember_window_geometry(self.settings):
            return

        geometry = self.settings.value(OPTIONS_GEOMETRY_KEY)
        if geometry:
            self.restoreGeometry(geometry)

    def _save_geometry(self):
        if remember_window_geometry(self.settings):
            self.settings.setValue(OPTIONS_GEOMETRY_KEY, self.saveGeometry())
        else:
            self.settings.remove(OPTIONS_GEOMETRY_KEY)
        self.settings.sync()

    def done(self, result):
        self._save_geometry()
        super().done(result)
