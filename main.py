import logging
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QSettings,
    QThread,
    QTimer,
    Qt,
    QUrl,
    Signal,
    Slot
)

from PySide6.QtGui import (
    QAction,
    QDesktopServices,
    QIcon,
    QKeySequence
)

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget
)

from about_dialog import AboutDialog
from components_dialog import ComponentsDialog
from options_dialog import OptionsDialog

from core.exporter import build_launch_script
from core.logging_setup import setup_logging
from core.paths import DATA_DIR, TRAINER_DIR
from core.preferences import (
    HIDE_EARLY_TRAINER_EXIT_KEY,
    HIDE_TRAINER_REQUIREMENTS_KEY,
    apply_theme,
    remember_window_geometry
)
from core.process_monitor import ProcessMonitor
from core.resources import resource_path
from core.scanner import scan_all_games
from core.session_manager import (
    LaunchCancelled,
    TrainerSessionManager
)
from core.storage import (
    import_trainer as store_trainer,
    remove_trainer as remove_stored_trainer
)
from core.steam import get_steam_info
from core.version import (
    APP_DESCRIPTION,
    APP_DISPLAY_VERSION,
    APP_NAME
)


STATUS_NAMES = {
    "NATIVE": "No Proton prefix",
    "READY_WITH_TRAINER": "Ready with trainer",
    "READY": "Ready - no trainer",
    "PROTON_DETECTED": "Proton prefix not initialized",
    "UNKNOWN": "Scan issue"
}


STATUS_ROLE = int(
    Qt.ItemDataRole.UserRole
) + 1


TRAINER_REQUIREMENTS_NOTICE_KEY = HIDE_TRAINER_REQUIREMENTS_KEY
EARLY_TRAINER_EXIT_NOTICE_KEY = HIDE_EARLY_TRAINER_EXIT_KEY


MAIN_GEOMETRY_KEY = "main/geometry"
MAIN_WINDOW_STATE_KEY = "main/window_state"
MAIN_SPLITTER_SIZES_KEY = "main/splitter_sizes"
MAIN_STATUS_FILTER_KEY = "main/status_filter"
MAIN_SEARCH_TEXT_KEY = "main/search_text"
MAIN_SELECTED_APPID_KEY = "main/selected_appid"
MAIN_LOG_VISIBLE_KEY = "main/log_visible"

EARLY_TRAINER_EXIT_SECONDS = 15


class SessionWorker(QObject):

    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)


    def __init__(
        self,
        game,
        action
    ):

        super().__init__()

        self.game = game
        self.action = action
        self.cancel_event = threading.Event()


    def cancel(self):

        self.cancel_event.set()


    @Slot()
    def run(self):

        try:

            session_manager = TrainerSessionManager()

            if self.action == "combined":

                session = session_manager.start(
                    self.game,
                    timeout=60,
                    trainer_delay=8,
                    cancel_event=self.cancel_event
                )

            elif self.action == "game":

                session = session_manager.launch_game(
                    self.game,
                    timeout=60,
                    cancel_event=self.cancel_event
                )

            elif self.action == "trainer":

                session = session_manager.launch_trainer(
                    self.game,
                    cancel_event=self.cancel_event
                )

            else:

                raise ValueError(
                    f"Unknown launch action: {self.action}"
                )

        except LaunchCancelled as error:

            self.cancelled.emit(
                str(error)
            )

            return

        except Exception as error:

            self.failed.emit(
                f"{type(error).__name__}: {error}"
            )

            return

        self.finished.emit(
            session
        )



class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self.settings = QSettings(
            APP_NAME,
            APP_NAME
        )

        self.logger = logging.getLogger(
            APP_NAME
        )

        self.saved_selected_appid = None

        self.games = []
        self.selected_game = None

        self.session_thread = None
        self.session_worker = None
        self.session_action = None
        self.session_cancel_requested = False
        self.active_session = None

        self.runtime_monitor = ProcessMonitor()
        self.verified_game_runtime = None
        self.verified_game_appid = None

        self.setWindowTitle(
            APP_NAME
        )

        self.setWindowIcon(
            QIcon(
                str(
                    resource_path(
                        "assets/trainerbridge.png"
                    )
                )
            )
        )

        self.setMinimumSize(
            1000,
            650
        )

        self._build_interface()
        self._build_menu()
        self._restore_ui_state()

        QTimer.singleShot(
            0,
            self._show_trainer_requirements_notice_if_needed
        )

        self.process_timer = QTimer(self)

        self.process_timer.timeout.connect(
            self._check_active_session
        )

        self.process_timer.start(
            1000
        )

        self.scan_games(
            select_appid=self.saved_selected_appid
        )


    def _build_interface(self):

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QVBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            12,
            10,
            12,
            10
        )

        main_layout.setSpacing(
            8
        )

        self.main_splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        self.main_splitter.setChildrenCollapsible(
            False
        )

        left_widget = QWidget()
        left_layout = QVBoxLayout(
            left_widget
        )

        left_layout.setContentsMargins(
            0,
            0,
            6,
            0
        )

        left_layout.setSpacing(
            6
        )

        self.search_field = QLineEdit()

        self.search_field.setPlaceholderText(
            "Search games..."
        )

        self.search_field.textChanged.connect(
            self.apply_filter
        )

        filter_layout = QHBoxLayout()

        filter_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        status_filter_label = QLabel(
            "Status:"
        )

        self.status_filter = QComboBox()

        self.status_filter.addItem(
            "All games",
            "ALL"
        )

        self.status_filter.addItem(
            "Supported Proton games",
            "PROTON"
        )

        self.status_filter.addItem(
            "Ready with trainer",
            "READY_WITH_TRAINER"
        )

        self.status_filter.addItem(
            "Ready - no trainer",
            "READY"
        )

        self.status_filter.addItem(
            "No Proton prefix",
            "NATIVE"
        )

        self.status_filter.addItem(
            "Scan issue",
            "UNKNOWN"
        )

        self.status_filter.currentIndexChanged.connect(
            self.apply_filter
        )

        self.rescan_button = QPushButton(
            "Rescan"
        )

        self.rescan_button.clicked.connect(
            self.scan_games
        )

        filter_layout.addWidget(
            self.search_field,
            2
        )

        filter_layout.addWidget(
            status_filter_label
        )

        filter_layout.addWidget(
            self.status_filter,
            1
        )

        filter_layout.addWidget(
            self.rescan_button
        )

        left_layout.addLayout(
            filter_layout
        )

        self.game_tree = QTreeWidget()

        self.game_tree.setColumnCount(
            4
        )

        self.game_tree.setHeaderLabels(
            [
                "Game",
                "AppID",
                "Proton",
                "Status"
            ]
        )

        self.game_tree.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        self.game_tree.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .SingleSelection
        )

        self.game_tree.setAlternatingRowColors(
            True
        )

        self.game_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )

        self.game_tree.customContextMenuRequested.connect(
            self._show_game_context_menu
        )

        self.game_tree.itemSelectionChanged.connect(
            self._game_selection_changed
        )

        header = self.game_tree.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents
        )

        left_layout.addWidget(
            self.game_tree,
            1
        )

        self.main_splitter.addWidget(
            left_widget
        )

        details_scroll = QScrollArea()

        details_scroll.setWidgetResizable(
            True
        )

        details_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        right_widget = QWidget()
        right_widget.setMinimumWidth(0)

        right_layout = QVBoxLayout(
            right_widget
        )

        right_layout.setContentsMargins(
            8,
            0,
            0,
            0
        )

        right_layout.setSpacing(
            8
        )

        actions_group = QGroupBox(
            "Actions"
        )

        actions_layout = QVBoxLayout(
            actions_group
        )

        self.start_button = QPushButton(
            "Launch Game + Trainer"
        )

        self.start_button.setDefault(
            True
        )

        self.start_button.setMinimumHeight(
            38
        )

        self.start_button.clicked.connect(
            self.start_selected_game
        )

        actions_layout.addWidget(
            self.start_button
        )

        fallback_button_layout = QHBoxLayout()

        self.launch_game_button = QPushButton(
            "Launch Game"
        )

        self.launch_game_button.clicked.connect(
            self.launch_game_only
        )

        self.launch_trainer_button = QPushButton(
            "Launch Trainer"
        )

        self.launch_trainer_button.clicked.connect(
            self.launch_trainer_only
        )

        fallback_button_layout.addWidget(
            self.launch_game_button
        )

        fallback_button_layout.addWidget(
            self.launch_trainer_button
        )

        actions_layout.addLayout(
            fallback_button_layout
        )

        management_button_layout = QHBoxLayout()

        self.import_button = QPushButton(
            "Import Trainer"
        )

        self.import_button.clicked.connect(
            self.import_selected_trainer
        )

        self.components_button = QPushButton(
            "Prefix Components"
        )

        self.components_button.clicked.connect(
            self.open_components_dialog
        )

        management_button_layout.addWidget(
            self.import_button
        )

        management_button_layout.addWidget(
            self.components_button
        )

        actions_layout.addLayout(
            management_button_layout
        )

        right_layout.addWidget(
            actions_group
        )

        details_group = QGroupBox(
            "Game Details"
        )

        form_layout = QFormLayout(
            details_group
        )

        form_layout.setFieldGrowthPolicy(
            QFormLayout
            .FieldGrowthPolicy
            .AllNonFixedFieldsGrow
        )

        self.name_value = QLabel("-")
        self.appid_value = QLabel("-")
        self.status_value = QLabel("-")
        self.proton_value = QLabel("-")
        self.prefix_value = QLabel("-")
        self.trainer_value = QLabel("-")

        detail_labels = [
            self.name_value,
            self.appid_value,
            self.status_value,
            self.proton_value,
            self.prefix_value,
            self.trainer_value
        ]

        for label in detail_labels:

            label.setWordWrap(True)
            label.setMinimumWidth(0)

            label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred
            )

            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

        form_layout.addRow(
            "Game:",
            self.name_value
        )

        form_layout.addRow(
            "AppID:",
            self.appid_value
        )

        form_layout.addRow(
            "Status:",
            self.status_value
        )

        form_layout.addRow(
            "Proton:",
            self.proton_value
        )

        form_layout.addRow(
            "Prefix:",
            self.prefix_value
        )

        form_layout.addRow(
            "Trainer:",
            self.trainer_value
        )

        right_layout.addWidget(
            details_group
        )

        right_layout.addStretch(
            1
        )

        details_scroll.setWidget(
            right_widget
        )

        self.main_splitter.addWidget(
            details_scroll
        )

        self.main_splitter.setStretchFactor(
            0,
            3
        )

        self.main_splitter.setStretchFactor(
            1,
            2
        )

        self.main_splitter.setSizes(
            [
                620,
                380
            ]
        )

        main_layout.addWidget(
            self.main_splitter,
            1
        )

        self.log_title = QLabel(
            "Live Log"
        )

        self.log_title.setStyleSheet(
            "font-weight: bold;"
        )

        main_layout.addWidget(
            self.log_title
        )

        self.log_output = QTextEdit()

        self.log_output.setReadOnly(
            True
        )

        self.log_output.setPlaceholderText(
            "TrainerBridge status..."
        )

        self.log_output.setMinimumHeight(
            150
        )

        main_layout.addWidget(
            self.log_output
        )

        self.log_visible = True
        self._set_log_visible(True)

        self.statusBar().showMessage(
            "Ready"
        )

        self._update_action_buttons()


    def _build_menu(self):

        file_menu = self.menuBar().addMenu(
            "&File"
        )

        self.import_action = QAction(
            "Import Trainer...",
            self
        )
        self.import_action.setShortcut(
            QKeySequence("Ctrl+I")
        )
        self.import_action.triggered.connect(
            self.import_selected_trainer
        )
        file_menu.addAction(
            self.import_action
        )

        self.remove_trainer_action = QAction(
            "Remove Trainer",
            self
        )
        self.remove_trainer_action.setShortcut(
            QKeySequence("Ctrl+Delete")
        )
        self.remove_trainer_action.triggered.connect(
            self.remove_selected_trainer
        )
        file_menu.addAction(
            self.remove_trainer_action
        )

        file_menu.addSeparator()

        self.open_data_folder_action = QAction(
            "Open Data Folder",
            self
        )
        self.open_data_folder_action.triggered.connect(
            self.open_data_folder
        )
        file_menu.addAction(
            self.open_data_folder_action
        )

        file_menu.addSeparator()

        exit_action = QAction(
            "Exit",
            self
        )
        exit_action.setShortcut(
            QKeySequence("Ctrl+Q")
        )
        exit_action.triggered.connect(
            self.close
        )
        file_menu.addAction(
            exit_action
        )

        game_menu = self.menuBar().addMenu(
            "&Game"
        )

        self.launch_combined_action = QAction(
            "Launch Game + Trainer",
            self
        )
        self.launch_combined_action.triggered.connect(
            self.start_selected_game
        )
        game_menu.addAction(
            self.launch_combined_action
        )

        self.launch_game_action = QAction(
            "Launch Game",
            self
        )
        self.launch_game_action.triggered.connect(
            self.launch_game_only
        )
        game_menu.addAction(
            self.launch_game_action
        )

        self.launch_trainer_action = QAction(
            "Launch Trainer",
            self
        )
        self.launch_trainer_action.triggered.connect(
            self.launch_trainer_only
        )
        game_menu.addAction(
            self.launch_trainer_action
        )

        game_menu.addSeparator()

        self.prefix_components_action = QAction(
            "Prefix Components...",
            self
        )
        self.prefix_components_action.setShortcut(
            QKeySequence("Alt+Return")
        )
        self.prefix_components_action.triggered.connect(
            self.open_components_dialog
        )
        game_menu.addAction(
            self.prefix_components_action
        )

        self.open_game_folder_action = QAction(
            "Open Game Folder",
            self
        )
        self.open_game_folder_action.triggered.connect(
            self.open_selected_game_folder
        )
        game_menu.addAction(
            self.open_game_folder_action
        )

        self.open_prefix_folder_action = QAction(
            "Open Prefix Folder",
            self
        )
        self.open_prefix_folder_action.triggered.connect(
            self.open_selected_prefix_folder
        )
        game_menu.addAction(
            self.open_prefix_folder_action
        )

        self.open_trainer_folder_action = QAction(
            "Open Trainer Folder",
            self
        )
        self.open_trainer_folder_action.triggered.connect(
            self.open_selected_trainer_folder
        )
        game_menu.addAction(
            self.open_trainer_folder_action
        )

        game_menu.addSeparator()

        self.export_script_action = QAction(
            "Export Launch Script...",
            self
        )
        self.export_script_action.triggered.connect(
            self.export_launch_script
        )
        game_menu.addAction(
            self.export_script_action
        )

        view_menu = self.menuBar().addMenu(
            "&View"
        )

        self.show_log_action = QAction(
            "Show Live Log",
            self
        )
        self.show_log_action.setCheckable(True)
        self.show_log_action.setShortcut(
            QKeySequence("Ctrl+L")
        )
        self.show_log_action.toggled.connect(
            self._show_log_toggled
        )
        view_menu.addAction(
            self.show_log_action
        )

        tools_menu = self.menuBar().addMenu(
            "&Tools"
        )

        self.rescan_action = QAction(
            "Rescan Steam Library",
            self
        )
        self.rescan_action.setShortcut(
            QKeySequence("Ctrl+R")
        )
        self.rescan_action.triggered.connect(
            self.scan_games
        )
        tools_menu.addAction(
            self.rescan_action
        )

        self.open_trainers_folder_action = QAction(
            "Open Trainers Folder",
            self
        )
        self.open_trainers_folder_action.triggered.connect(
            self.open_trainers_folder
        )
        tools_menu.addAction(
            self.open_trainers_folder_action
        )

        tools_menu.addSeparator()

        self.options_action = QAction(
            "Options...",
            self
        )
        self.options_action.setShortcut(
            QKeySequence("Ctrl+,")
        )
        self.options_action.triggered.connect(
            self._show_options_dialog
        )
        tools_menu.addAction(
            self.options_action
        )

        help_menu = self.menuBar().addMenu(
            "&Help"
        )

        about_action = QAction(
            "About...",
            self
        )
        about_action.triggered.connect(
            self._show_about_dialog
        )
        help_menu.addAction(
            about_action
        )

        self.context_menu_action = QAction(
            "Open Game Context Menu",
            self.game_tree
        )
        self.context_menu_action.setShortcut(
            QKeySequence("Shift+F10")
        )
        self.context_menu_action.setShortcutContext(
            Qt.ShortcutContext.WidgetWithChildrenShortcut
        )
        self.context_menu_action.triggered.connect(
            self._show_game_context_menu_for_keyboard
        )
        self.game_tree.addAction(
            self.context_menu_action
        )

        self._update_action_buttons()
        self._set_log_visible(self.log_visible)


    def _show_about_dialog(
        self,
        checked=False
    ):

        del checked

        dialog = AboutDialog(
            self
        )

        dialog.exec()


    def _show_options_dialog(
        self,
        checked=False
    ):

        del checked

        dialog = OptionsDialog(
            self
        )
        dialog.exec()

        self._set_log_visible(
            self.settings.value(
                MAIN_LOG_VISIBLE_KEY,
                self.log_visible,
                type=bool
            )
        )


    def _show_game_context_menu(
        self,
        position
    ):

        item = self.game_tree.itemAt(
            position
        )

        if item is not None:
            self.game_tree.setCurrentItem(item)

        if self.selected_game is None:
            return

        menu = QMenu(self)
        menu.addAction(self.launch_combined_action)
        menu.addAction(self.launch_game_action)
        menu.addAction(self.launch_trainer_action)
        menu.addSeparator()
        menu.addAction(self.import_action)
        menu.addAction(self.remove_trainer_action)
        menu.addAction(self.open_trainer_folder_action)
        menu.addSeparator()
        menu.addAction(self.prefix_components_action)
        menu.addAction(self.open_prefix_folder_action)
        menu.addAction(self.open_game_folder_action)
        menu.addSeparator()
        menu.addAction(self.export_script_action)

        menu.exec(
            self.game_tree.viewport().mapToGlobal(
                position
            )
        )


    def _show_game_context_menu_for_keyboard(self):

        current_item = self.game_tree.currentItem()

        if current_item is None:
            return

        rectangle = self.game_tree.visualItemRect(
            current_item
        )

        position = rectangle.center()
        self._show_game_context_menu(position)


    def _open_folder(
        self,
        folder,
        description
    ):

        if not folder:

            QMessageBox.information(
                self,
                f"{description} unavailable",
                f"No {description.lower()} is available for the selected game."
            )

            return

        folder = Path(folder)

        if not folder.is_dir():

            QMessageBox.warning(
                self,
                f"{description} not found",
                f"The folder does not exist:\n{folder}"
            )

            return

        opened = QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(folder)
            )
        )

        if not opened:

            QMessageBox.warning(
                self,
                "Folder could not be opened",
                f"TrainerBridge could not open:\n{folder}"
            )


    def open_data_folder(self):

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True
        )
        self._open_folder(
            DATA_DIR,
            "Data folder"
        )


    def open_trainers_folder(self):

        TRAINER_DIR.mkdir(
            parents=True,
            exist_ok=True
        )
        self._open_folder(
            TRAINER_DIR,
            "Trainers folder"
        )


    def open_selected_game_folder(self):

        game = self.selected_game
        self._open_folder(
            game.game_path if game else None,
            "Game folder"
        )


    def open_selected_prefix_folder(self):

        game = self.selected_game
        self._open_folder(
            game.prefix if game else None,
            "Prefix folder"
        )


    def open_selected_trainer_folder(self):

        game = self.selected_game

        trainer_folder = (
            Path(game.trainer_path).parent
            if game and game.trainer_path
            else None
        )

        self._open_folder(
            trainer_folder,
            "Trainer folder"
        )


    def remove_selected_trainer(self):

        game = self.selected_game

        if not game or not game.trainer_path:
            return

        if self._trainer_is_running():

            QMessageBox.warning(
                self,
                "Trainer is still running",
                "Close the trainer before removing it from TrainerBridge."
            )

            return

        answer = QMessageBox.warning(
            self,
            "Remove trainer",
            (
                f"Remove the configured trainer for {game.name}?\n\n"
                f"Managed file:\n{game.trainer_path}\n\n"
                "The original downloaded file is not affected."
            ),
            (
                QMessageBox.StandardButton.Yes
                |
                QMessageBox.StandardButton.Cancel
            ),
            QMessageBox.StandardButton.Cancel
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        try:

            remove_stored_trainer(
                game.appid
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Trainer removal failed",
                str(error)
            )

            return

        self._append_log(
            f"Trainer removed for {game.name}."
        )

        self.scan_games(
            select_appid=game.appid
        )


    def export_launch_script(self):

        game = self.selected_game

        if not game:
            return

        safe_name = "".join(
            character
            if character.isalnum() or character in "-_"
            else "-"
            for character in game.name
        ).strip("-") or game.appid

        default_path = (
            Path.home()
            / f"TrainerBridge-{safe_name}.sh"
        )

        target_file, _ = QFileDialog.getSaveFileName(
            self,
            f"Export launch script for {game.name}",
            str(default_path),
            "Shell scripts (*.sh);;All files (*)"
        )

        if not target_file:
            return

        target_path = Path(target_file)

        if target_path.suffix.lower() != ".sh":
            target_path = target_path.with_suffix(".sh")

        try:

            script = build_launch_script(
                game
            )

            target_path.write_text(
                script,
                encoding="utf-8"
            )
            target_path.chmod(0o755)

        except Exception as error:

            QMessageBox.critical(
                self,
                "Launch script export failed",
                str(error)
            )

            return

        self._append_log(
            f"Launch script exported: {target_path}"
        )

        QMessageBox.information(
            self,
            "Launch script exported",
            (
                f"The executable launch script was saved to:\n"
                f"{target_path}\n\n"
                "It uses absolute paths. Re-export it after moving Steam, "
                "the game library, Proton, or the trainer."
            )
        )


    def _restore_ui_state(self):

        if remember_window_geometry(self.settings):

            geometry = self.settings.value(
                MAIN_GEOMETRY_KEY
            )

            if geometry:

                self.restoreGeometry(
                    geometry
                )

            window_state = self.settings.value(
                MAIN_WINDOW_STATE_KEY
            )

            if window_state:

                self.restoreState(
                    window_state
                )

            splitter_sizes = self.settings.value(
                MAIN_SPLITTER_SIZES_KEY
            )

            if isinstance(splitter_sizes, (list, tuple)):

                try:

                    sizes = [
                        int(value)
                        for value in splitter_sizes
                    ]

                except (TypeError, ValueError):

                    sizes = []

                if len(sizes) == 2:

                    self.main_splitter.setSizes(
                        sizes
                    )

        saved_status = self.settings.value(
            MAIN_STATUS_FILTER_KEY,
            "ALL"
        )

        status_index = self.status_filter.findData(
            saved_status
        )

        if status_index >= 0:

            self.status_filter.setCurrentIndex(
                status_index
            )

        saved_search = self.settings.value(
            MAIN_SEARCH_TEXT_KEY,
            ""
        )

        self.search_field.setText(
            str(saved_search or "")
        )

        selected_appid = self.settings.value(
            MAIN_SELECTED_APPID_KEY
        )

        if selected_appid:

            self.saved_selected_appid = str(
                selected_appid
            )

        log_visible = self.settings.value(
            MAIN_LOG_VISIBLE_KEY,
            True,
            type=bool
        )

        self._set_log_visible(
            log_visible
        )


    def _save_ui_state(self):

        if remember_window_geometry(self.settings):

            self.settings.setValue(
                MAIN_GEOMETRY_KEY,
                self.saveGeometry()
            )

            self.settings.setValue(
                MAIN_WINDOW_STATE_KEY,
                self.saveState()
            )

            self.settings.setValue(
                MAIN_SPLITTER_SIZES_KEY,
                self.main_splitter.sizes()
            )

        else:

            self.settings.remove(MAIN_GEOMETRY_KEY)
            self.settings.remove(MAIN_WINDOW_STATE_KEY)
            self.settings.remove(MAIN_SPLITTER_SIZES_KEY)

        self.settings.setValue(
            MAIN_STATUS_FILTER_KEY,
            self.status_filter.currentData()
        )

        self.settings.setValue(
            MAIN_SEARCH_TEXT_KEY,
            self.search_field.text()
        )

        selected_appid = self._get_selected_appid()

        if selected_appid:

            self.settings.setValue(
                MAIN_SELECTED_APPID_KEY,
                str(selected_appid)
            )

        else:

            self.settings.remove(
                MAIN_SELECTED_APPID_KEY
            )

        self.settings.setValue(
            MAIN_LOG_VISIBLE_KEY,
            self.log_visible
        )

        self.settings.sync()


    def closeEvent(
        self,
        event
    ):

        self._save_ui_state()

        super().closeEvent(
            event
        )


    def _toggle_log_visibility(self):

        self._set_log_visible(
            not self.log_visible
        )

        self.settings.setValue(
            MAIN_LOG_VISIBLE_KEY,
            self.log_visible
        )


    def _set_log_visible(
        self,
        visible
    ):

        self.log_visible = bool(
            visible
        )

        self.log_title.setVisible(
            self.log_visible
        )

        self.log_output.setVisible(
            self.log_visible
        )

        if hasattr(self, "show_log_action"):

            self.show_log_action.blockSignals(True)
            self.show_log_action.setChecked(
                self.log_visible
            )
            self.show_log_action.blockSignals(False)



    def _show_log_toggled(
        self,
        visible
    ):

        self._set_log_visible(
            visible
        )

        self.settings.setValue(
            MAIN_LOG_VISIBLE_KEY,
            self.log_visible
        )


    def _show_trainer_requirements_notice_if_needed(
        self
    ):

        notice_hidden = self.settings.value(
            TRAINER_REQUIREMENTS_NOTICE_KEY,
            False,
            type=bool
        )

        if notice_hidden:
            return

        self._show_trainer_requirements_notice()


    def _show_trainer_requirements_notice(
        self,
        checked=False
    ):

        del checked

        message_box = QMessageBox(
            self
        )

        message_box.setIcon(
            QMessageBox.Icon.Information
        )

        message_box.setWindowTitle(
            "Windows trainer requirements"
        )

        message_box.setText(
            "Some Windows trainers require additional "
            "runtime components."
        )

        message_box.setInformativeText(
            "Examples include .NET Framework, .NET/.NET Core "
            "and Microsoft Visual C++ runtimes. TrainerBridge "
            "cannot reliably determine which components a "
            "specific trainer requires. Check the trainer "
            "author's documentation and install only the "
            "required components through Prefix Components.\n\n"
            "Prefix changes can affect game compatibility."
        )

        do_not_show_again = QCheckBox(
            "Don't show this message again"
        )

        message_box.setCheckBox(
            do_not_show_again
        )

        message_box.setStandardButtons(
            QMessageBox.StandardButton.Ok
        )

        message_box.exec()

        if do_not_show_again.isChecked():

            self.settings.setValue(
                TRAINER_REQUIREMENTS_NOTICE_KEY,
                True
            )

    def _append_log(
        self,
        message
    ):

        self.logger.info(
            message
        )

        self.log_output.append(
            message
        )


    def _get_selected_appid(self):

        selected_items = self.game_tree.selectedItems()

        if not selected_items:
            return None

        return selected_items[0].data(
            0,
            Qt.ItemDataRole.UserRole
        )


    def _find_game(
        self,
        appid
    ):

        for game in self.games:

            if game.appid == appid:
                return game

        return None


    def scan_games(
        self,
        checked=False,
        select_appid=None
    ):

        del checked

        if select_appid is None:

            select_appid = self._get_selected_appid()

        self.statusBar().showMessage(
            "Scanning Steam games..."
        )

        self.rescan_button.setEnabled(
            False
        )

        if hasattr(self, "rescan_action"):
            self.rescan_action.setEnabled(False)

        QApplication.setOverrideCursor(
            Qt.CursorShape.WaitCursor
        )

        try:

            games = scan_all_games()

            self.games = sorted(
                games,
                key=lambda game: game.name.lower()
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Scan failed",
                str(error)
            )

            self._append_log(
                f"Scan failed: {error}"
            )

            return

        finally:

            QApplication.restoreOverrideCursor()

            self.rescan_button.setEnabled(
                True
            )

            if hasattr(self, "rescan_action"):
                self.rescan_action.setEnabled(True)

        steam_info = get_steam_info()

        if steam_info[
            "install_path"
        ]:

            self._append_log(
                "Steam installation: "
                f"{steam_info['display_name']}"
            )

            self._append_log(
                "Steam data directory: "
                f"{steam_info['install_path']}"
            )

        else:

            self._append_log(
                "No supported Steam data directory was found."
            )

        self._populate_game_tree()

        self.apply_filter()

        if select_appid:

            self._select_game_by_appid(
                select_appid
            )

        else:

            self._select_first_recommended_game()

        self.statusBar().showMessage(
            f"{len(self.games)} games found"
        )

        self._append_log(
            f"Found {len(self.games)} Steam games."
        )


    def _populate_game_tree(self):

        self.game_tree.clear()

        for game in self.games:

            proton_name = (
                game.proton_name
                if game.proton_name
                else "-"
            )

            status_name = STATUS_NAMES.get(
                game.status,
                game.status
            )

            item = QTreeWidgetItem(
                [
                    game.name,
                    game.appid,
                    proton_name,
                    status_name
                ]
            )

            item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                game.appid
            )

            item.setData(
                0,
                STATUS_ROLE,
                game.status
            )

            if game.status == "NATIVE":

                native_tooltip = (
                    "TrainerBridge could not find a Proton prefix. "
                    "The game may be native Linux, still downloading, "
                    "or not yet initialized through Proton."
                )

                item.setToolTip(
                    0,
                    native_tooltip
                )

                item.setToolTip(
                    3,
                    native_tooltip
                )

            self.game_tree.addTopLevelItem(
                item
            )


    def apply_filter(
        self,
        *unused_arguments
    ):

        del unused_arguments

        search_text = (
            self.search_field.text()
            .strip()
            .lower()
        )

        selected_status = (
            self.status_filter.currentData()
        )

        for index in range(
            self.game_tree.topLevelItemCount()
        ):

            item = self.game_tree.topLevelItem(
                index
            )

            searchable_text = " ".join(
                [
                    item.text(0),
                    item.text(1),
                    item.text(2),
                    item.text(3)
                ]
            ).lower()

            game_status = item.data(
                0,
                STATUS_ROLE
            )

            search_matches = (
                not search_text
                or
                search_text in searchable_text
            )

            if selected_status == "ALL":

                status_matches = True

            elif selected_status == "PROTON":

                status_matches = (
                    game_status != "NATIVE"
                )

            else:

                status_matches = (
                    game_status == selected_status
                )

            item.setHidden(
                not (
                    search_matches
                    and
                    status_matches
                )
            )

        selected_items = (
            self.game_tree.selectedItems()
        )

        if (
            selected_items
            and
            selected_items[0].isHidden()
        ):

            self.game_tree.clearSelection()

            self.selected_game = None

            self._update_details()
            self._update_action_buttons()

            self._select_first_visible_game()


    def _select_first_visible_game(self):

        for index in range(
            self.game_tree.topLevelItemCount()
        ):

            item = self.game_tree.topLevelItem(
                index
            )

            if item.isHidden():
                continue

            self.game_tree.setCurrentItem(
                item
            )

            return


    def _select_game_by_appid(
        self,
        appid
    ):

        for index in range(
            self.game_tree.topLevelItemCount()
        ):

            item = self.game_tree.topLevelItem(
                index
            )

            item_appid = item.data(
                0,
                Qt.ItemDataRole.UserRole
            )

            if item_appid != appid:
                continue

            self.game_tree.setCurrentItem(
                item
            )

            self.game_tree.scrollToItem(
                item
            )

            return


    def _select_first_recommended_game(self):

        preferred_statuses = [
            "READY_WITH_TRAINER",
            "READY"
        ]

        for status in preferred_statuses:

            for game in self.games:

                if game.status != status:
                    continue

                self._select_game_by_appid(
                    game.appid
                )

                return


    def _game_selection_changed(self):

        appid = self._get_selected_appid()

        self.selected_game = self._find_game(
            appid
        )

        self._update_details()
        self._update_action_buttons()


    def _update_details(self):

        game = self.selected_game

        if not game:

            self.name_value.setText("-")
            self.appid_value.setText("-")
            self.status_value.setText("-")
            self.proton_value.setText("-")
            self.prefix_value.setText("-")
            self.trainer_value.setText("-")

            return

        self.name_value.setText(
            game.name
        )

        self.appid_value.setText(
            game.appid
        )

        status_text = STATUS_NAMES.get(
            game.status,
            game.status
        )

        if game.status == "NATIVE":

            status_text += (
                " - not supported by TrainerBridge"
            )

        self.status_value.setText(
            status_text
        )

        self.proton_value.setText(
            self._display_path(
                game.proton_path
            )
        )

        self.prefix_value.setText(
            self._display_path(
                game.prefix
            )
        )

        self.trainer_value.setText(
            self._display_path(
                game.trainer_path
            )
        )


    def _display_path(
        self,
        path
    ):

        if not path:
            return "-"

        return str(
            Path(path)
        )


    def _trainer_is_running(self):

        if not self.active_session:
            return False

        trainer_process = self.active_session.get(
            "trainer_process"
        )

        if not trainer_process:
            return False

        return trainer_process.poll() is None


    def _verified_game_is_running(
        self,
        game=None
    ):

        if not self.verified_game_runtime:
            return False

        if not self.verified_game_appid:
            return False

        if game is not None:

            return (
                str(game.appid)
                ==
                str(self.verified_game_appid)
            )

        return True


    def _session_is_starting(self):

        return self.session_thread is not None


    def _update_action_buttons(self):

        game = self.selected_game

        selection_actions = [
            "import_action",
            "remove_trainer_action",
            "launch_combined_action",
            "launch_game_action",
            "launch_trainer_action",
            "prefix_components_action",
            "open_game_folder_action",
            "open_prefix_folder_action",
            "open_trainer_folder_action",
            "export_script_action"
        ]

        if self._session_is_starting():

            cancel_text = (
                "Cancelling..."
                if self.session_cancel_requested
                else "Cancel Launch"
            )

            self.start_button.setText(
                cancel_text
            )

            self.start_button.setEnabled(
                not self.session_cancel_requested
            )

            self.import_button.setEnabled(False)
            self.components_button.setEnabled(False)
            self.launch_game_button.setEnabled(False)
            self.launch_trainer_button.setEnabled(False)

            for action_name in selection_actions:

                action = getattr(
                    self,
                    action_name,
                    None
                )

                if action is not None:
                    action.setEnabled(False)

            launch_combined_action = getattr(
                self,
                "launch_combined_action",
                None
            )

            if launch_combined_action is not None:

                launch_combined_action.setText(
                    cancel_text
                )

                launch_combined_action.setEnabled(
                    not self.session_cancel_requested
                )

            return

        self.start_button.setText(
            "Launch Game + Trainer"
        )

        launch_combined_action = getattr(
            self,
            "launch_combined_action",
            None
        )

        if launch_combined_action is not None:
            launch_combined_action.setText(
                "Launch Game + Trainer"
            )

        if not game:

            self.import_button.setText("Import Trainer")
            self.import_button.setEnabled(False)
            self.components_button.setEnabled(False)
            self.launch_game_button.setEnabled(False)
            self.launch_trainer_button.setEnabled(False)
            self.start_button.setEnabled(False)

            for action_name in selection_actions:
                action = getattr(self, action_name, None)
                if action is not None:
                    action.setEnabled(False)

            import_action = getattr(self, "import_action", None)
            if import_action is not None:
                import_action.setText("Import Trainer...")

            return

        is_proton_game = game.status != "NATIVE"
        trainer_is_running = self._trainer_is_running()
        verified_game_is_running = self._verified_game_is_running(
            game
        )

        session_is_busy = trainer_is_running

        trainer_exists = (
            game.trainer_path is not None
            and
            Path(game.trainer_path).is_file()
        )

        import_text = (
            "Replace Trainer"
            if trainer_exists
            else "Import Trainer"
        )
        self.import_button.setText(import_text)

        import_action = getattr(self, "import_action", None)
        if import_action is not None:
            import_action.setText(f"{import_text}...")

        can_import = (
            is_proton_game
            and
            not session_is_busy
        )

        can_open_components = (
            is_proton_game
            and
            game.prefix is not None
            and
            Path(game.prefix).is_dir()
            and
            not session_is_busy
            and
            not verified_game_is_running
        )

        game_is_ready_for_trainer = (
            trainer_exists
            and
            game.prefix is not None
            and
            Path(game.prefix).is_dir()
            and
            game.proton_path is not None
            and
            (Path(game.proton_path) / "proton").is_file()
        )

        can_launch_game = (
            is_proton_game
            and
            not session_is_busy
            and
            not verified_game_is_running
        )

        can_launch_trainer = (
            game_is_ready_for_trainer
            and
            verified_game_is_running
            and
            not session_is_busy
        )

        can_launch_combined = (
            game_is_ready_for_trainer
            and
            not session_is_busy
        )

        self.import_button.setEnabled(can_import)
        self.components_button.setEnabled(can_open_components)
        self.launch_game_button.setEnabled(can_launch_game)
        self.launch_trainer_button.setEnabled(can_launch_trainer)
        self.start_button.setEnabled(can_launch_combined)

        action_states = {
            "import_action": can_import,
            "remove_trainer_action": trainer_exists and not session_is_busy,
            "launch_combined_action": can_launch_combined,
            "launch_game_action": can_launch_game,
            "launch_trainer_action": can_launch_trainer,
            "prefix_components_action": can_open_components,
            "open_game_folder_action": bool(
                game.game_path and Path(game.game_path).is_dir()
            ),
            "open_prefix_folder_action": bool(
                game.prefix and Path(game.prefix).is_dir()
            ),
            "open_trainer_folder_action": trainer_exists,
            "export_script_action": game_is_ready_for_trainer
        }

        for action_name, enabled in action_states.items():
            action = getattr(self, action_name, None)
            if action is not None:
                action.setEnabled(enabled)


    def import_selected_trainer(self):

        game = self.selected_game

        if not game:
            return

        replacing_trainer = game.trainer_path is not None

        trainer_file, _ = QFileDialog.getOpenFileName(
            self,
            (
                f"Select a replacement trainer for {game.name}"
                if replacing_trainer
                else f"Select a trainer for {game.name}"
            ),
            str(Path.home()),
            "Windows executables (*.exe);;All files (*)"
        )

        if not trainer_file:
            return

        try:

            target_file = store_trainer(
                game.appid,
                trainer_file
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Import failed",
                str(error)
            )

            self._append_log(
                f"Trainer import failed: {error}"
            )

            return

        self._append_log(
            f"Trainer imported: {target_file}"
        )

        QMessageBox.information(
            self,
            (
                "Trainer replaced"
                if replacing_trainer
                else "Trainer imported"
            ),
            (
                "The trainer was successfully replaced in TrainerBridge."
                if replacing_trainer
                else "The trainer was successfully copied into TrainerBridge."
            )
        )

        self.scan_games(
            select_appid=game.appid
        )


    def _open_components_for_game(
        self,
        game
    ):

        if not game:
            return

        dialog = ComponentsDialog(
            game,
            self
        )

        dialog.exec()

        if dialog.prefix_restored:
            self.scan_games(
                select_appid=game.appid
            )


    def open_components_dialog(self):

        self._open_components_for_game(
            self.selected_game
        )


    def launch_game_only(self):

        self._start_launch_action(
            "game"
        )


    def launch_trainer_only(self):

        game = self.selected_game

        if not game:
            return

        if not self._verified_game_is_running(game):

            QMessageBox.information(
                self,
                "Game not verified",
                (
                    "Launch Game must first confirm that the "
                    "game's Proton session is ready before "
                    "Launch Trainer becomes available."
                )
            )

            return

        self._start_launch_action(
            "trainer"
        )


    def start_selected_game(self):

        if self._session_is_starting():

            self._cancel_active_launch()
            return

        self._start_launch_action(
            "combined"
        )


    def _start_launch_action(
        self,
        action
    ):

        game = self.selected_game

        if not game:
            return

        if self._session_is_starting():
            return

        if self._trainer_is_running():

            QMessageBox.information(
                self,
                "Trainer already running",
                (
                    "A TrainerBridge trainer session is already active."
                )
            )

            return

        action_labels = {
            "combined": "game and trainer",
            "game": "game",
            "trainer": "trainer"
        }

        action_label = action_labels.get(
            action,
            action
        )

        self._append_log(
            f"Starting {action_label} for {game.name}..."
        )

        self.statusBar().showMessage(
            f"Starting {action_label} for {game.name}..."
        )

        self.session_action = action
        self.session_cancel_requested = False

        self.session_thread = QThread(self)
        self.session_worker = SessionWorker(
            game,
            action
        )

        self.session_worker.moveToThread(
            self.session_thread
        )

        self.session_thread.started.connect(
            self.session_worker.run
        )

        self.session_worker.finished.connect(
            self._session_started
        )

        self.session_worker.failed.connect(
            self._session_failed
        )

        self.session_worker.cancelled.connect(
            self._session_cancelled
        )

        self.session_worker.finished.connect(
            self.session_thread.quit
        )

        self.session_worker.failed.connect(
            self.session_thread.quit
        )

        self.session_worker.cancelled.connect(
            self.session_thread.quit
        )

        self.session_worker.finished.connect(
            self.session_worker.deleteLater
        )

        self.session_worker.failed.connect(
            self.session_worker.deleteLater
        )

        self.session_worker.cancelled.connect(
            self.session_worker.deleteLater
        )

        self.session_thread.finished.connect(
            self._session_thread_finished
        )

        self._update_action_buttons()

        self.session_thread.start()


    def _cancel_active_launch(self):

        if not self._session_is_starting():
            return

        if self.session_cancel_requested:
            return

        self.session_cancel_requested = True

        self._append_log(
            "Cancelling the automatic launch sequence. "
            "The game will not be stopped."
        )

        self.statusBar().showMessage(
            "Cancelling launch..."
        )

        if self.session_worker is not None:
            self.session_worker.cancel()

        self._update_action_buttons()


    @Slot(object)
    def _session_started(
        self,
        session
    ):

        action = session.get(
            "action",
            "combined"
        )

        game = session["game"]
        runtime = session["runtime"]

        self.verified_game_runtime = runtime
        self.verified_game_appid = str(
            game.appid
        )

        self._append_log(
            f"Detected {game.name}."
        )

        self._append_log(
            f"Game executable: {runtime.game_executable}"
        )

        self._append_log(
            f"Game PID: {runtime.game_pid}"
        )

        if action == "game":

            self.active_session = None

            self._append_log(
                "Proton session verified. Launch Trainer is now available."
            )

            self.statusBar().showMessage(
                "Game is running - trainer can be launched"
            )

        elif action == "trainer":

            self.active_session = session

            self._append_log(
                "Trainer started."
            )

            self.statusBar().showMessage(
                "Trainer is running"
            )

        else:

            self.active_session = session

            self._append_log(
                "Trainer started."
            )

            self.statusBar().showMessage(
                "Game and trainer are running"
            )

        self._update_action_buttons()


    @Slot(str)
    def _session_cancelled(
        self,
        message
    ):

        self.active_session = None

        cancel_message = (
            message
            or
            "Launch cancelled. The game was left running."
        )

        self._append_log(
            cancel_message
        )

        self.statusBar().showMessage(
            "Launch cancelled - game left running"
        )


    @Slot(str)
    def _session_failed(
        self,
        message
    ):

        if self.session_cancel_requested:

            self._session_cancelled(
                "Launch cancelled. The game was left running."
            )

            return

        self.active_session = None

        self._append_log(
            f"Launch failed: {message}"
        )

        self.statusBar().showMessage(
            "Launch failed"
        )

        QMessageBox.critical(
            self,
            "TrainerBridge launch failed",
            message
        )


    @Slot()
    def _session_thread_finished(self):

        thread = self.session_thread

        self.session_thread = None
        self.session_worker = None
        self.session_action = None
        self.session_cancel_requested = False

        if thread:
            thread.deleteLater()

        self._update_action_buttons()


    def _show_early_trainer_exit_warning(
        self,
        game,
        return_code,
        runtime_seconds
    ):

        message_box = QMessageBox(
            self
        )

        message_box.setIcon(
            QMessageBox.Icon.Warning
        )

        message_box.setWindowTitle(
            "Trainer exited unexpectedly"
        )

        message_box.setText(
            f"The trainer for {game.name} exited shortly "
            f"after launch with code {return_code}."
        )

        message_box.setInformativeText(
            "The trainer may require additional runtime "
            "components such as .NET or Microsoft Visual C++. "
            "Check the trainer author's documentation and use "
            "Prefix Components to install only the components "
            "it requires.\n\n"
            "Close the game before modifying its Proton prefix.\n\n"
            f"Trainer runtime: {runtime_seconds:.1f} seconds."
        )

        components_button = message_box.addButton(
            "Open Prefix Components",
            QMessageBox.ButtonRole.ActionRole
        )

        message_box.addButton(
            QMessageBox.StandardButton.Close
        )

        do_not_show_again = QCheckBox(
            "Do not show this hint again"
        )
        message_box.setCheckBox(
            do_not_show_again
        )

        message_box.exec()

        if do_not_show_again.isChecked():

            self.settings.setValue(
                EARLY_TRAINER_EXIT_NOTICE_KEY,
                True
            )

        if message_box.clickedButton() is components_button:

            self._open_components_for_game(
                game
            )


    def _check_active_session(self):

        if self.verified_game_runtime:

            current_runtime = self.runtime_monitor.get_runtime(
                self.verified_game_appid
            )

            game_stopped = (
                current_runtime is None
                or
                current_runtime.game_pid
                !=
                self.verified_game_runtime.game_pid
            )

            if game_stopped:

                stopped_appid = self.verified_game_appid

                self.verified_game_runtime = None
                self.verified_game_appid = None

                self._append_log(
                    f"Verified game {stopped_appid} exited."
                )

                if not self._trainer_is_running():

                    self.statusBar().showMessage(
                        "Game exited"
                    )

            else:

                self.verified_game_runtime = current_runtime

        if self.active_session:

            trainer_process = self.active_session.get(
                "trainer_process"
            )

            if trainer_process:

                return_code = trainer_process.poll()

                if return_code is not None:

                    session = self.active_session

                    game = session.get(
                        "game"
                    )

                    trainer_started_at = session.get(
                        "trainer_started_at"
                    )

                    runtime_seconds = None

                    if trainer_started_at is not None:

                        runtime_seconds = max(
                            0.0,
                            time.monotonic()
                            -
                            float(trainer_started_at)
                        )

                    if game:

                        self._append_log(
                            (
                                f"Trainer for {game.name} exited "
                                f"with code {return_code}."
                            )
                        )

                    self.active_session = None

                    if self._verified_game_is_running():

                        self.statusBar().showMessage(
                            "Trainer exited - game is still running"
                        )

                    else:

                        self.statusBar().showMessage(
                            "Trainer exited"
                        )

                    exited_early = (
                        return_code != 0
                        and
                        runtime_seconds is not None
                        and
                        runtime_seconds
                        <=
                        EARLY_TRAINER_EXIT_SECONDS
                    )

                    show_early_exit_hint = not self.settings.value(
                        EARLY_TRAINER_EXIT_NOTICE_KEY,
                        False,
                        type=bool
                    )

                    if exited_early and game:

                        self._append_log(
                            "The trainer exited shortly after launch. "
                            "It may require additional Prefix Components."
                        )

                        if show_early_exit_hint:

                            self._show_early_trainer_exit_warning(
                                game,
                                return_code,
                                runtime_seconds
                            )

        self._update_action_buttons()



def run_self_test():

    checks = []

    try:

        test_application = (
            QApplication.instance()
            or
            QApplication(
                [APP_NAME, "--self-test"]
            )
        )

        test_widget = QWidget()
        test_widget.setWindowTitle(
            APP_NAME
        )

        test_application.processEvents()

        checks.append(
            ("Qt platform initialization", True, "OK")
        )

        test_widget.deleteLater()

    except Exception as error:

        checks.append(
            ("Qt platform initialization", False, str(error))
        )

    try:

        import vdf  # noqa: F401

        checks.append(
            ("vdf import", True, "OK")
        )

    except Exception as error:

        checks.append(
            ("vdf import", False, str(error))
        )

    try:

        import zstandard  # noqa: F401

        checks.append(
            ("zstandard import", True, "OK")
        )

    except Exception as error:

        checks.append(
            ("zstandard import", False, str(error))
        )

    for relative_path in (
        "assets/trainerbridge.png",
        "assets/THIRD_PARTY_NOTICES.txt"
    ):

        path = resource_path(
            relative_path
        )

        checks.append(
            (
                relative_path,
                path.is_file(),
                str(path)
            )
        )

    checks.append(
        (
            "application metadata",
            bool(APP_NAME and APP_DISPLAY_VERSION),
            f"{APP_NAME} {APP_DISPLAY_VERSION}"
        )
    )

    print(
        f"{APP_NAME} self-test"
    )

    failed = False

    for name, success, detail in checks:

        status = (
            "PASS"
            if success
            else "FAIL"
        )

        print(
            f"[{status}] {name}: {detail}"
        )

        if not success:
            failed = True

    return 1 if failed else 0


def main():

    if "--self-test" in sys.argv:

        return run_self_test()

    log_file = setup_logging()

    print(
        f"Log file: {log_file}"
    )

    application = QApplication(
        sys.argv
    )

    application.setOrganizationName(
        APP_NAME
    )

    application.setApplicationName(
        APP_NAME
    )

    application.setApplicationDisplayName(
        APP_NAME
    )

    application.setApplicationVersion(
        APP_DISPLAY_VERSION
    )

    application.setWindowIcon(
        QIcon(
            str(
                resource_path(
                    "assets/trainerbridge.png"
                )
            )
        )
    )

    apply_theme(
        application
    )

    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":

    sys.exit(
        main()
    )
