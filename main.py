import sys
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    QThread,
    QTimer,
    Qt,
    Signal,
    Slot
)

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
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

from components_dialog import ComponentsDialog

from core.process_monitor import ProcessMonitor
from core.scanner import scan_all_games
from core.session_manager import TrainerSessionManager
from core.storage import import_trainer as store_trainer


STATUS_NAMES = {
    "NATIVE": "Native Linux game",
    "READY_WITH_TRAINER": "Ready with trainer",
    "READY": "Ready — no trainer",
    "PROTON_DETECTED": "Proton detected",
    "UNKNOWN": "Unknown"
}


class SessionWorker(QObject):

    finished = Signal(object)
    failed = Signal(str)


    def __init__(
        self,
        game,
        action
    ):

        super().__init__()

        self.game = game
        self.action = action


    @Slot()
    def run(self):

        try:

            session_manager = TrainerSessionManager()

            if self.action == "combined":

                session = session_manager.start(
                    self.game,
                    timeout=120,
                    trainer_delay=8
                )

            elif self.action == "game":

                session = session_manager.launch_game(
                    self.game,
                    timeout=120
                )

            elif self.action == "trainer":

                session = session_manager.launch_trainer(
                    self.game
                )

            else:

                raise ValueError(
                    f"Unknown launch action: {self.action}"
                )

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

        self.games = []
        self.selected_game = None

        self.session_thread = None
        self.session_worker = None
        self.active_session = None

        self.runtime_monitor = ProcessMonitor()
        self.verified_game_runtime = None
        self.verified_game_appid = None

        self.setWindowTitle(
            "TrainerBridge"
        )

        self.setMinimumSize(
            1000,
            650
        )

        self._build_interface()

        self.process_timer = QTimer(self)

        self.process_timer.timeout.connect(
            self._check_active_session
        )

        self.process_timer.start(
            1000
        )

        self.scan_games()


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

        header_widget = QFrame()

        header_widget.setFixedHeight(
            66
        )

        header_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        header_layout = QVBoxLayout(
            header_widget
        )

        header_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        header_layout.setSpacing(
            2
        )

        title = QLabel(
            "TrainerBridge"
        )

        title.setStyleSheet(
            """
            font-size: 24px;
            font-weight: bold;
            """
        )

        subtitle = QLabel(
            "Launch Steam games running through Proton "
            "together with their Windows trainers"
        )

        subtitle.setStyleSheet(
            "color: gray;"
        )

        title.setWordWrap(False)
        subtitle.setWordWrap(False)

        header_layout.addWidget(
            title
        )

        header_layout.addWidget(
            subtitle
        )

        header_layout.addStretch(1)

        main_layout.addWidget(
            header_widget
        )

        search_layout = QHBoxLayout()

        self.search_field = QLineEdit()

        self.search_field.setPlaceholderText(
            "Search games..."
        )

        self.search_field.textChanged.connect(
            self.apply_filter
        )

        self.rescan_button = QPushButton(
            "Rescan"
        )

        self.rescan_button.clicked.connect(
            self.scan_games
        )

        search_layout.addWidget(
            self.search_field,
            1
        )

        search_layout.addWidget(
            self.rescan_button
        )

        main_layout.addLayout(
            search_layout
        )

        splitter = QSplitter(
            Qt.Orientation.Horizontal
        )

        splitter.setChildrenCollapsible(
            False
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

        splitter.addWidget(
            self.game_tree
        )

        details_scroll = QScrollArea()

        details_scroll.setWidgetResizable(
            True
        )

        details_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        details_widget = QWidget()
        details_widget.setMinimumWidth(0)

        details_layout = QVBoxLayout(
            details_widget
        )

        details_layout.setContentsMargins(
            8,
            0,
            0,
            0
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

        details_layout.addWidget(
            details_group
        )

        first_button_layout = QHBoxLayout()

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

        first_button_layout.addWidget(
            self.import_button
        )

        first_button_layout.addWidget(
            self.components_button
        )

        details_layout.addLayout(
            first_button_layout
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

        details_layout.addLayout(
            fallback_button_layout
        )

        self.start_button = QPushButton(
            "Launch Game + Trainer"
        )

        self.start_button.setDefault(
            True
        )

        self.start_button.clicked.connect(
            self.start_selected_game
        )

        details_layout.addWidget(
            self.start_button
        )

        self.log_output = QTextEdit()

        self.log_output.setReadOnly(
            True
        )

        self.log_output.setPlaceholderText(
            "TrainerBridge status..."
        )

        details_layout.addWidget(
            self.log_output,
            1
        )

        details_scroll.setWidget(
            details_widget
        )

        splitter.addWidget(
            details_scroll
        )

        splitter.setStretchFactor(
            0,
            3
        )

        splitter.setStretchFactor(
            1,
            2
        )

        splitter.setSizes(
            [
                600,
                400
            ]
        )

        main_layout.addWidget(
            splitter,
            1
        )

        self.statusBar().showMessage(
            "Ready"
        )

        self._update_action_buttons()


    def _append_log(
        self,
        message
    ):

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

        self._populate_game_tree()

        self.apply_filter(
            self.search_field.text()
        )

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

            self.game_tree.addTopLevelItem(
                item
            )


    def apply_filter(
        self,
        text
    ):

        search_text = text.strip().lower()

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

            should_hide = (
                search_text
                and
                search_text not in searchable_text
            )

            item.setHidden(
                bool(should_hide)
            )


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
            "READY",
            "PROTON_DETECTED"
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

        self.status_value.setText(
            STATUS_NAMES.get(
                game.status,
                game.status
            )
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

        if not game:

            self.import_button.setEnabled(False)
            self.components_button.setEnabled(False)
            self.launch_game_button.setEnabled(False)
            self.launch_trainer_button.setEnabled(False)
            self.start_button.setEnabled(False)

            return

        is_proton_game = game.status != "NATIVE"
        action_is_running = self._session_is_starting()
        trainer_is_running = self._trainer_is_running()
        verified_game_is_running = self._verified_game_is_running(
            game
        )

        session_is_busy = (
            action_is_running
            or
            trainer_is_running
        )

        self.import_button.setEnabled(
            is_proton_game
            and
            not session_is_busy
        )

        self.components_button.setEnabled(
            is_proton_game
            and
            game.prefix is not None
            and
            not session_is_busy
            and
            not verified_game_is_running
        )

        game_is_ready_for_trainer = (
            game.trainer_path is not None
            and
            game.prefix is not None
            and
            game.proton_path is not None
        )

        self.launch_game_button.setEnabled(
            is_proton_game
            and
            not session_is_busy
            and
            not verified_game_is_running
        )

        self.launch_trainer_button.setEnabled(
            game_is_ready_for_trainer
            and
            verified_game_is_running
            and
            not session_is_busy
        )

        self.start_button.setEnabled(
            game_is_ready_for_trainer
            and
            not session_is_busy
        )


    def import_selected_trainer(self):

        game = self.selected_game

        if not game:
            return

        trainer_file, _ = QFileDialog.getOpenFileName(
            self,
            f"Select a trainer for {game.name}",
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
            "Trainer imported",
            (
                "The trainer was successfully copied "
                "into TrainerBridge."
            )
        )

        self.scan_games(
            select_appid=game.appid
        )


    def open_components_dialog(self):

        game = self.selected_game

        if not game:
            return

        dialog = ComponentsDialog(
            game,
            self
        )

        dialog.exec()


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
                    "Launch Game must successfully detect the "
                    "actual game executable before Launch Trainer "
                    "becomes available."
                )
            )

            return

        self._start_launch_action(
            "trainer"
        )


    def start_selected_game(self):

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

        self.session_worker.finished.connect(
            self.session_thread.quit
        )

        self.session_worker.failed.connect(
            self.session_thread.quit
        )

        self.session_worker.finished.connect(
            self.session_worker.deleteLater
        )

        self.session_worker.failed.connect(
            self.session_worker.deleteLater
        )

        self.session_thread.finished.connect(
            self._session_thread_finished
        )

        self._update_action_buttons()

        self.session_thread.start()


    @Slot(object)
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
                "Game launch verified. Launch Trainer is now available."
            )

            self.statusBar().showMessage(
                "Game is running — trainer can be launched"
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
    def _session_failed(
        self,
        message
    ):

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

        if thread:
            thread.deleteLater()

        self._update_action_buttons()


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

                    game = self.active_session.get(
                        "game"
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
                            "Trainer exited — game is still running"
                        )

                    else:

                        self.statusBar().showMessage(
                            "Trainer exited"
                        )

        self._update_action_buttons()


def main():

    application = QApplication(
        sys.argv
    )

    application.setApplicationName(
        "TrainerBridge"
    )

    window = MainWindow()
    window.show()

    sys.exit(
        application.exec()
    )


if __name__ == "__main__":

    main()
