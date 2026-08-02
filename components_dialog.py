import threading
from datetime import datetime

from PySide6.QtCore import (
    QObject,
    QSettings,
    QThread,
    QTimer,
    Qt,
    Signal,
    Slot
)

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget
)

from core.backup_manager import (
    BackupCancelled,
    BackupManager
)
from core.preferences import (
    BACKUP_METHOD_AUTO,
    BACKUP_METHOD_KEY,
    BACKUP_POLICY_ALWAYS,
    BACKUP_POLICY_ASK,
    BACKUP_POLICY_KEY,
    BACKUP_POLICY_NEVER,
    remember_window_geometry
)
from core.protontricks import (
    ProtontricksManager,
    SUPPORTED_CATEGORIES,
    WINDOWS_VERSION_LABELS,
    WINDOWS_VERSION_VERBS
)

from core.version import APP_NAME


COMPONENT_NAME_ROLE = int(Qt.ItemDataRole.UserRole)
COMPONENT_INSTALLED_ROLE = COMPONENT_NAME_ROLE + 1
COMPONENT_CATEGORY_ROLE = COMPONENT_NAME_ROLE + 2
COMPONENT_DESCRIPTION_ROLE = COMPONENT_NAME_ROLE + 3

COMPONENTS_GEOMETRY_KEY = "components/geometry"
COMPONENTS_LOG_VISIBLE_KEY = "components/log_visible"
COMPONENTS_CURRENT_TAB_KEY = "components/current_tab"
COMPONENTS_INSTALLED_ONLY_KEY = "components/installed_only"



class ComponentLoadWorker(QObject):

    finished = Signal(object)
    failed = Signal(str)


    def __init__(
        self,
        manager,
        appid,
        force_refresh
    ):

        super().__init__()

        self.manager = manager
        self.appid = appid
        self.force_refresh = force_refresh


    @Slot()
    def run(self):

        try:

            catalog = self.manager.load_components(
                self.appid,
                force_refresh=self.force_refresh
            )

        except Exception as error:

            self.failed.emit(
                f"{type(error).__name__}: {error}"
            )

            return

        self.finished.emit(
            catalog
        )


class ComponentInstallWorker(QObject):

    finished = Signal(str)
    failed = Signal(str)


    def __init__(
        self,
        manager,
        appid,
        component_names
    ):

        super().__init__()

        self.manager = manager
        self.appid = appid
        self.component_names = tuple(
            component_names
        )


    @Slot()
    def run(self):

        try:

            output = (
                self.manager
                .install_components_capture(
                    self.appid,
                    self.component_names
                )
            )

        except Exception as error:

            self.failed.emit(
                f"{type(error).__name__}: {error}"
            )

            return

        self.finished.emit(
            output
        )


class BackupWorker(QObject):

    finished = Signal(object)
    failed = Signal(str)
    # Python objects are used for byte counters because Qt's plain int
    # signal type is limited to signed 32-bit values (about 2 GiB).
    progress = Signal(object, object, str)


    def __init__(
        self,
        backup_manager,
        action,
        requested_method=BACKUP_METHOD_AUTO,
        components=(),
        windows_version=None
    ):

        super().__init__()

        self.backup_manager = backup_manager
        self.action = action
        self.requested_method = requested_method
        self.components = tuple(components)
        self.windows_version = windows_version
        self.cancel_event = threading.Event()


    def cancel(self):
        self.cancel_event.set()


    def _report_progress(
        self,
        processed,
        total,
        message
    ):

        self.progress.emit(
            int(processed) if processed is not None else None,
            int(total) if total is not None else None,
            str(message)
        )


    @Slot()
    def run(self):

        try:

            if self.action == "create":

                result = self.backup_manager.create_backup(
                    requested_method=self.requested_method,
                    components=self.components,
                    windows_version=self.windows_version,
                    progress_callback=self._report_progress,
                    cancel_event=self.cancel_event
                )

            elif self.action == "restore":

                result = self.backup_manager.restore_backup(
                    progress_callback=self._report_progress
                )

            elif self.action == "delete":

                result = self.backup_manager.delete_backup()

            else:

                raise ValueError(
                    f"Unknown backup action: {self.action}"
                )

        except BackupCancelled as error:

            self.failed.emit(
                str(error)
            )

            return

        except Exception as error:

            self.failed.emit(
                f"{type(error).__name__}: {error}"
            )

            return

        self.finished.emit(
            result
        )


class ComponentsDialog(QDialog):

    def __init__(
        self,
        game,
        parent=None
    ):

        super().__init__(parent)

        self.settings = QSettings(
            APP_NAME,
            APP_NAME
        )

        self.game = game
        self.manager = ProtontricksManager.detect()
        self.backup_manager = BackupManager(game)

        self.components = []
        self.component_trees = {}
        self.component_items = {}
        self.category_order = [
            *SUPPORTED_CATEGORIES.keys(),
            "all"
        ]

        self.load_thread = None
        self.load_worker = None

        self.install_thread = None
        self.install_worker = None

        self.backup_thread = None
        self.backup_worker = None
        self.backup_action = None
        self.pending_install_components = None
        self.refresh_after_backup_delete = False
        self.prefix_restored = False

        self.reload_after_install = False
        self.updating_items = False

        self.setWindowTitle(
            f"Prefix Components - {game.name}"
        )

        self.resize(
            1000,
            700
        )

        self.setMinimumSize(
            840,
            580
        )

        self._build_interface()
        self._restore_ui_state()

        QTimer.singleShot(
            0,
            self._initial_load
        )


    def _build_interface(self):

        main_layout = QVBoxLayout(self)

        main_layout.setContentsMargins(
            12,
            10,
            12,
            10
        )

        main_layout.setSpacing(
            8
        )

        technical_header_layout = QHBoxLayout()

        technical_header_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.technical_details_button = QPushButton(
            "Show technical details"
        )

        self.technical_details_button.clicked.connect(
            self._toggle_technical_details
        )

        technical_header_layout.addStretch(
            1
        )

        technical_header_layout.addWidget(
            self.technical_details_button
        )

        main_layout.addLayout(
            technical_header_layout
        )

        self.technical_details_widget = QWidget()

        technical_layout = QFormLayout(
            self.technical_details_widget
        )

        technical_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.game_value = QLabel(
            self.game.name
        )

        self.appid_value = QLabel(
            str(self.game.appid)
        )

        self.game_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.appid_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.prefix_value = QLabel(
            str(self.game.prefix or "-")
        )

        self.prefix_value.setWordWrap(
            True
        )

        self.prefix_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        if self.manager:

            protontricks_text = (
                self.manager.installation.display_name
            )

        else:

            protontricks_text = (
                "Not found"
            )

        self.protontricks_label = QLabel(
            protontricks_text
        )

        self.windows_version_label = QLabel(
            "Loading..."
        )

        technical_layout.addRow(
            "Game:",
            self.game_value
        )

        technical_layout.addRow(
            "AppID:",
            self.appid_value
        )

        technical_layout.addRow(
            "Prefix:",
            self.prefix_value
        )

        technical_layout.addRow(
            "Protontricks:",
            self.protontricks_label
        )

        technical_layout.addRow(
            "Windows version:",
            self.windows_version_label
        )

        self.technical_details_widget.setVisible(
            False
        )

        main_layout.addWidget(
            self.technical_details_widget
        )

        filter_layout = QHBoxLayout()

        self.search_field = QLineEdit()

        self.search_field.setPlaceholderText(
            "Search the current category..."
        )

        self.search_field.textChanged.connect(
            self.apply_filter
        )

        self.installed_only_checkbox = QCheckBox(
            "Show installed only"
        )

        self.installed_only_checkbox.toggled.connect(
            self.apply_filter
        )

        self.refresh_button = QPushButton(
            "Refresh catalog"
        )

        self.refresh_button.clicked.connect(
            self.refresh_catalog
        )

        filter_layout.addWidget(
            self.search_field,
            1
        )

        filter_layout.addWidget(
            self.installed_only_checkbox
        )

        filter_layout.addWidget(
            self.refresh_button
        )

        self.progress_bar = QProgressBar()

        self.progress_bar.setRange(
            0,
            0
        )

        self.progress_bar.setVisible(
            False
        )

        self.status_label = QLabel(
            "Ready"
        )

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(
            self.progress_bar,
            1
        )

        self.cancel_operation_button = QPushButton(
            "Cancel backup"
        )
        self.cancel_operation_button.setVisible(False)
        self.cancel_operation_button.clicked.connect(
            self._cancel_backup_operation
        )
        progress_layout.addWidget(
            self.cancel_operation_button
        )

        main_layout.addLayout(
            progress_layout
        )

        main_layout.addWidget(
            self.status_label
        )

        backup_group = QGroupBox(
            "Safety Backup"
        )
        backup_layout = QHBoxLayout(
            backup_group
        )

        self.backup_status_label = QLabel(
            "No safety backup exists for this game."
        )
        self.backup_status_label.setWordWrap(True)

        self.restore_backup_button = QPushButton(
            "Restore Backup"
        )
        self.restore_backup_button.clicked.connect(
            self.restore_backup
        )

        self.delete_backup_button = QPushButton(
            "Delete Backup"
        )
        self.delete_backup_button.clicked.connect(
            self.delete_backup
        )

        backup_layout.addWidget(
            self.backup_status_label,
            1
        )
        backup_layout.addWidget(
            self.restore_backup_button
        )
        backup_layout.addWidget(
            self.delete_backup_button
        )

        # Keep catalog controls immediately next to the catalog they affect.
        main_layout.addLayout(
            filter_layout
        )

        self.category_tabs = QTabWidget()

        self.category_tabs.currentChanged.connect(
            self.apply_filter
        )

        for category in self.category_order:

            include_category = (
                category == "all"
            )

            tree = self._create_component_tree(
                include_category=include_category
            )

            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)

            tab_layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            tab_layout.addWidget(
                tree
            )

            self.component_trees[category] = tree

            if category == "all":

                title = "All"

            else:

                title = SUPPORTED_CATEGORIES[
                    category
                ]

            self.category_tabs.addTab(
                tab_widget,
                self._escape_tab_title(title)
            )

        main_layout.addWidget(
            self.category_tabs,
            1
        )

        # Backup controls belong with the lower operation/output area rather
        # than the technical header. This keeps the catalog itself visually
        # dominant while the safety controls remain easy to reach.
        main_layout.addWidget(
            backup_group
        )

        log_header_layout = QHBoxLayout()

        log_header_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        log_title = QLabel(
            "Protontricks Output"
        )

        log_title.setStyleSheet(
            "font-weight: bold;"
        )

        self.log_toggle_button = QPushButton()

        self.log_toggle_button.clicked.connect(
            self._toggle_log_visibility
        )

        log_header_layout.addWidget(
            log_title
        )

        log_header_layout.addStretch(
            1
        )

        log_header_layout.addWidget(
            self.log_toggle_button
        )

        main_layout.addLayout(
            log_header_layout
        )

        self.output_field = QTextEdit()

        self.output_field.setReadOnly(
            True
        )

        self.output_field.setMaximumHeight(
            170
        )

        self.output_field.setPlaceholderText(
            "Protontricks output..."
        )

        main_layout.addWidget(
            self.output_field
        )

        self.log_visible = True
        self._set_log_visible(True)

        button_layout = QHBoxLayout()

        self.selection_label = QLabel(
            "0 components selected"
        )

        self.clear_selection_button = QPushButton(
            "Clear selection"
        )

        self.clear_selection_button.clicked.connect(
            self.clear_selection
        )

        self.install_button = QPushButton(
            "Install selected components"
        )

        self.install_button.clicked.connect(
            self.install_selected_components
        )

        self.close_button = QPushButton(
            "Close"
        )

        self.close_button.clicked.connect(
            self.accept
        )

        button_layout.addWidget(
            self.selection_label
        )

        button_layout.addStretch(
            1
        )

        button_layout.addWidget(
            self.clear_selection_button
        )

        button_layout.addWidget(
            self.install_button
        )

        button_layout.addWidget(
            self.close_button
        )

        main_layout.addLayout(
            button_layout
        )

        self._refresh_backup_status()
        self._update_buttons()


    def _create_component_tree(
        self,
        include_category=False
    ):

        tree = QTreeWidget()

        if include_category:

            tree.setColumnCount(
                4
            )

            tree.setHeaderLabels(
                [
                    "Component",
                    "Category",
                    "Status",
                    "Description"
                ]
            )

        else:

            tree.setColumnCount(
                3
            )

            tree.setHeaderLabels(
                [
                    "Component",
                    "Status",
                    "Description"
                ]
            )

        tree.setSelectionBehavior(
            QAbstractItemView
            .SelectionBehavior
            .SelectRows
        )

        tree.setSelectionMode(
            QAbstractItemView
            .SelectionMode
            .ExtendedSelection
        )

        tree.setAlternatingRowColors(
            True
        )

        tree.itemChanged.connect(
            self._component_check_changed
        )

        header = tree.header()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents
        )

        if include_category:

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
                QHeaderView.ResizeMode.Stretch
            )

        else:

            header.setSectionResizeMode(
                1,
                QHeaderView.ResizeMode.ResizeToContents
            )

            header.setSectionResizeMode(
                2,
                QHeaderView.ResizeMode.Stretch
            )

        return tree


    def _escape_tab_title(
        self,
        title
    ):

        return str(title).replace(
            "&",
            "&&"
        )


    def _toggle_technical_details(self):

        visible = not self.technical_details_widget.isVisible()

        self.technical_details_widget.setVisible(
            visible
        )

        self.technical_details_button.setText(
            "Hide technical details"
            if visible
            else "Show technical details"
        )


    def _toggle_log_visibility(self):

        self._set_log_visible(
            not self.log_visible
        )

        self.settings.setValue(
            COMPONENTS_LOG_VISIBLE_KEY,
            self.log_visible
        )


    def _set_log_visible(
        self,
        visible
    ):

        self.log_visible = bool(
            visible
        )

        self.output_field.setVisible(
            self.log_visible
        )

        self.log_toggle_button.setText(
            "Hide Output"
            if self.log_visible
            else "Show Output"
        )


    def _restore_ui_state(self):

        if remember_window_geometry(self.settings):

            geometry = self.settings.value(
                COMPONENTS_GEOMETRY_KEY
            )

            if geometry:

                self.restoreGeometry(
                    geometry
                )

        installed_only = self.settings.value(
            COMPONENTS_INSTALLED_ONLY_KEY,
            False,
            type=bool
        )

        self.installed_only_checkbox.setChecked(
            installed_only
        )

        saved_category = self.settings.value(
            COMPONENTS_CURRENT_TAB_KEY,
            self.category_order[0]
        )

        if saved_category in self.category_order:

            self.category_tabs.setCurrentIndex(
                self.category_order.index(
                    saved_category
                )
            )

        log_visible = self.settings.value(
            COMPONENTS_LOG_VISIBLE_KEY,
            True,
            type=bool
        )

        self._set_log_visible(
            log_visible
        )


    def _save_ui_state(self):

        if remember_window_geometry(self.settings):

            self.settings.setValue(
                COMPONENTS_GEOMETRY_KEY,
                self.saveGeometry()
            )

        else:

            self.settings.remove(
                COMPONENTS_GEOMETRY_KEY
            )

        self.settings.setValue(
            COMPONENTS_INSTALLED_ONLY_KEY,
            self.installed_only_checkbox.isChecked()
        )

        self.settings.setValue(
            COMPONENTS_CURRENT_TAB_KEY,
            self._current_category()
        )

        self.settings.setValue(
            COMPONENTS_LOG_VISIBLE_KEY,
            self.log_visible
        )

        self.settings.sync()


    def _initial_load(self):

        if not self.manager:

            self.status_label.setText(
                "Protontricks is not installed."
            )

            QMessageBox.warning(
                self,
                "Protontricks not found",
                (
                    "TrainerBridge could not find either a "
                    "system installation or the Flatpak version "
                    "of Protontricks."
                )
            )

            self._update_buttons()

            return

        self.load_components(
            force_refresh=False
        )


    def _is_busy(self):

        return (
            self.load_thread is not None
            or
            self.install_thread is not None
            or
            self.backup_thread is not None
        )


    def _set_busy(
        self,
        busy,
        message=None
    ):

        self.progress_bar.setVisible(
            busy
        )

        if busy and self.backup_thread is None:
            self.progress_bar.setRange(0, 0)

        if not busy:
            self.cancel_operation_button.setVisible(False)
            self.progress_bar.setRange(0, 0)

        self.search_field.setEnabled(
            not busy
        )

        self.installed_only_checkbox.setEnabled(
            not busy
        )

        self.category_tabs.setEnabled(
            not busy
        )

        self.refresh_button.setEnabled(
            not busy
            and
            self.manager is not None
        )

        self.close_button.setEnabled(
            not busy
        )

        if message:

            self.status_label.setText(
                message
            )

        self._update_buttons()


    def load_components(
        self,
        force_refresh=False
    ):

        if not self.manager:
            return

        if self._is_busy():
            return

        if force_refresh:

            message = (
                "Reloading the full Protontricks catalog..."
            )

        else:

            message = (
                "Loading components and installation status..."
            )

        self._set_busy(
            True,
            message
        )

        self.load_thread = QThread(self)

        self.load_worker = ComponentLoadWorker(
            manager=self.manager,
            appid=self.game.appid,
            force_refresh=force_refresh
        )

        self.load_worker.moveToThread(
            self.load_thread
        )

        self.load_thread.started.connect(
            self.load_worker.run
        )

        self.load_worker.finished.connect(
            self._components_loaded
        )

        self.load_worker.failed.connect(
            self._component_load_failed
        )

        self.load_worker.finished.connect(
            self.load_thread.quit
        )

        self.load_worker.failed.connect(
            self.load_thread.quit
        )

        self.load_worker.finished.connect(
            self.load_worker.deleteLater
        )

        self.load_worker.failed.connect(
            self.load_worker.deleteLater
        )

        self.load_thread.finished.connect(
            self._load_thread_finished
        )

        self.load_thread.start()


    def refresh_catalog(self):

        self.load_components(
            force_refresh=True
        )


    @Slot(object)
    @Slot(object)
    def _components_loaded(
        self,
        catalog
    ):

        self.components = list(
            catalog.components
        )

        self._populate_component_trees()

        cache_text = (
            "loaded from cache"
            if catalog.from_cache
            else "loaded from Protontricks"
        )

        installed_count = sum(
            1
            for component in self.components
            if component.installed
        )

        self.protontricks_label.setText(
            (
                f"{self.manager.installation.display_name} "
                f"— {catalog.version}"
            )
        )

        if catalog.windows_version:

            windows_label = WINDOWS_VERSION_LABELS.get(
                catalog.windows_version,
                catalog.windows_version
            )

            self.windows_version_label.setText(
                windows_label
            )

        else:

            self.windows_version_label.setText(
                "Could not be detected"
            )

        self.status_label.setText(
            (
                f"{len(self.components)} components {cache_text}; "
                f"{installed_count} installed or active."
            )
        )

        self._set_busy(
            False
        )

        self.apply_filter()


    @Slot(str)
    def _component_load_failed(
        self,
        message
    ):

        self.status_label.setText(
            "Components could not be loaded."
        )

        self.output_field.setPlainText(
            message
        )

        self._set_log_visible(
            True
        )

        self._set_busy(
            False
        )

        QMessageBox.critical(
            self,
            "Loading failed",
            message
        )


    @Slot()
    def _load_thread_finished(self):

        thread = self.load_thread

        self.load_thread = None
        self.load_worker = None

        if thread:
            thread.deleteLater()

        self._update_buttons()


    def _populate_component_trees(self):

        selected_names = set(
            self._checked_component_names()
        )

        self.updating_items = True

        try:

            for tree in self.component_trees.values():
                tree.clear()

            self.component_items = {}

            category_counts = {
                category: 0
                for category in SUPPORTED_CATEGORIES
            }

            for component in self.components:

                category_tree = self.component_trees.get(
                    component.category
                )

                all_tree = self.component_trees.get(
                    "all"
                )

                if category_tree:

                    self._add_component_item(
                        category_tree,
                        component,
                        selected_names,
                        include_category=False
                    )

                    category_counts[
                        component.category
                    ] += 1

                if all_tree:

                    self._add_component_item(
                        all_tree,
                        component,
                        selected_names,
                        include_category=True
                    )

            for index, category in enumerate(
                self.category_order
            ):

                if category == "all":

                    title = "All"
                    count = len(self.components)

                else:

                    title = SUPPORTED_CATEGORIES[
                        category
                    ]

                    count = category_counts[
                        category
                    ]

                self.category_tabs.setTabText(
                    index,
                    self._escape_tab_title(
                        f"{title} ({count})"
                    )
                )

        finally:

            self.updating_items = False

        self.apply_filter()
        self._update_buttons()


    def _add_component_item(
        self,
        tree,
        component,
        selected_names,
        include_category=False
    ):

        if component.name in WINDOWS_VERSION_VERBS:

            installed_text = (
                "Active"
                if component.installed
                else "Not active"
            )

        elif component.category == "settings":

            installed_text = (
                "Applied previously"
                if component.installed
                else "Not applied"
            )

        else:

            installed_text = (
                "Installed"
                if component.installed
                else "Not installed"
            )

        if include_category:

            values = [
                component.name,
                SUPPORTED_CATEGORIES.get(
                    component.category,
                    component.category
                ),
                installed_text,
                component.description
            ]

        else:

            values = [
                component.name,
                installed_text,
                component.description
            ]

        item = QTreeWidgetItem(
            values
        )

        item.setData(
            0,
            COMPONENT_NAME_ROLE,
            component.name
        )

        item.setData(
            0,
            COMPONENT_INSTALLED_ROLE,
            component.installed
        )

        item.setData(
            0,
            COMPONENT_CATEGORY_ROLE,
            component.category
        )

        item.setData(
            0,
            COMPONENT_DESCRIPTION_ROLE,
            component.description
        )

        if component.installed:

            item.setCheckState(
                0,
                Qt.CheckState.Checked
            )

            item.setFlags(
                item.flags()
                &
                ~Qt.ItemFlag.ItemIsUserCheckable
            )

        else:

            item.setFlags(
                item.flags()
                |
                Qt.ItemFlag.ItemIsUserCheckable
            )

            item.setCheckState(
                0,
                (
                    Qt.CheckState.Checked
                    if component.name in selected_names
                    else Qt.CheckState.Unchecked
                )
            )

        tree.addTopLevelItem(
            item
        )

        self.component_items.setdefault(
            component.name,
            []
        ).append(
            item
        )


    def _current_category(self):

        index = self.category_tabs.currentIndex()

        if (
            index < 0
            or
            index >= len(self.category_order)
        ):

            return self.category_order[0]

        return self.category_order[index]


    def apply_filter(self, *unused_arguments):

        del unused_arguments

        search_text = (
            self.search_field.text()
            .strip()
            .lower()
        )

        installed_only = (
            self.installed_only_checkbox.isChecked()
        )

        for category, tree in self.component_trees.items():

            visible_count = 0

            for index in range(
                tree.topLevelItemCount()
            ):

                item = tree.topLevelItem(
                    index
                )

                component_name = str(
                    item.data(
                        0,
                        COMPONENT_NAME_ROLE
                    )
                    or ""
                )

                description = str(
                    item.data(
                        0,
                        COMPONENT_DESCRIPTION_ROLE
                    )
                    or ""
                )

                item_category = str(
                    item.data(
                        0,
                        COMPONENT_CATEGORY_ROLE
                    )
                    or ""
                )

                category_title = SUPPORTED_CATEGORIES.get(
                    item_category,
                    item_category
                )

                installed = bool(
                    item.data(
                        0,
                        COMPONENT_INSTALLED_ROLE
                    )
                )

                searchable_text = (
                    f"{component_name} "
                    f"{description} "
                    f"{category_title}"
                ).lower()

                matches_search = (
                    not search_text
                    or
                    search_text in searchable_text
                )

                matches_installed = (
                    not installed_only
                    or
                    installed
                )

                visible = (
                    matches_search
                    and
                    matches_installed
                )

                item.setHidden(
                    not visible
                )

                if visible:
                    visible_count += 1

            tree.setProperty(
                "visible_count",
                visible_count
            )

        if self.components and not self._is_busy():

            current_category = self._current_category()
            current_tree = self.component_trees[
                current_category
            ]

            visible_count = current_tree.property(
                "visible_count"
            ) or 0

            if current_category == "all":

                category_total = len(
                    self.components
                )

                category_title = "All"

            else:

                category_total = sum(
                    1
                    for component in self.components
                    if component.category == current_category
                )

                category_title = SUPPORTED_CATEGORIES[
                    current_category
                ]

            self.status_label.setText(
                (
                    f"Showing {visible_count} of "
                    f"{category_total} components in "
                    f"{category_title}."
                )
            )

        self._update_buttons()


    def _checked_component_names(self):

        selected_names = set()

        for component_name, items in self.component_items.items():

            if not items:
                continue

            item = items[0]

            installed = bool(
                item.data(
                    0,
                    COMPONENT_INSTALLED_ROLE
                )
            )

            if installed:
                continue

            if (
                item.checkState(0)
                ==
                Qt.CheckState.Checked
            ):

                selected_names.add(
                    component_name
                )

        return sorted(
            selected_names
        )


    def _component_check_changed(
        self,
        item,
        column
    ):

        del column

        if self.updating_items:
            return

        component_name = item.data(
            0,
            COMPONENT_NAME_ROLE
        )

        if not component_name:
            return

        check_state = item.checkState(
            0
        )

        self.updating_items = True

        try:

            for matching_item in self.component_items.get(
                component_name,
                []
            ):

                installed = bool(
                    matching_item.data(
                        0,
                        COMPONENT_INSTALLED_ROLE
                    )
                )

                if installed:
                    continue

                if matching_item.checkState(0) != check_state:

                    matching_item.setCheckState(
                        0,
                        check_state
                    )

            if (
                component_name in WINDOWS_VERSION_VERBS
                and
                check_state == Qt.CheckState.Checked
            ):

                for other_name in WINDOWS_VERSION_VERBS:

                    if other_name == component_name:
                        continue

                    for other_item in self.component_items.get(
                        other_name,
                        []
                    ):

                        other_installed = bool(
                            other_item.data(
                                0,
                                COMPONENT_INSTALLED_ROLE
                            )
                        )

                        if other_installed:
                            continue

                        other_item.setCheckState(
                            0,
                            Qt.CheckState.Unchecked
                        )

        finally:

            self.updating_items = False

        self._update_buttons()


    def clear_selection(self):

        if self._is_busy():
            return

        self.updating_items = True

        try:

            for tree in self.component_trees.values():

                for index in range(
                    tree.topLevelItemCount()
                ):

                    item = tree.topLevelItem(
                        index
                    )

                    installed = bool(
                        item.data(
                            0,
                            COMPONENT_INSTALLED_ROLE
                        )
                    )

                    if installed:
                        continue

                    item.setCheckState(
                        0,
                        Qt.CheckState.Unchecked
                    )

        finally:

            self.updating_items = False

        self._update_buttons()


    def _update_buttons(self):

        required_widgets = (
            "selection_label",
            "install_button",
            "clear_selection_button",
            "restore_backup_button",
            "delete_backup_button"
        )

        if not all(hasattr(self, name) for name in required_widgets):
            return

        selected_names = self._checked_component_names()
        selected_count = len(selected_names)

        self.selection_label.setText(
            (
                "1 component selected"
                if selected_count == 1
                else f"{selected_count} components selected"
            )
        )

        self.install_button.setText(
            (
                "Install selected component"
                if selected_count == 1
                else (
                    "Install selected components"
                    if selected_count == 0
                    else (
                        "Install selected components "
                        f"({selected_count})"
                    )
                )
            )
        )

        can_install = (
            self.manager is not None
            and
            selected_count > 0
            and
            not self._is_busy()
        )

        self.install_button.setEnabled(
            can_install
        )

        self.clear_selection_button.setEnabled(
            selected_count > 0
            and
            not self._is_busy()
        )

        backup_exists = self.backup_manager.load_info() is not None

        self.restore_backup_button.setEnabled(
            backup_exists
            and
            not self._is_busy()
        )

        self.delete_backup_button.setEnabled(
            backup_exists
            and
            not self._is_busy()
        )


    def _refresh_backup_status(self):

        info = self.backup_manager.load_info()

        if info is None:

            self.backup_status_label.setText(
                "No safety backup exists for this game."
            )

            self._update_buttons()
            return

        method_labels = {
            "compressed": "Compressed archive",
            "reflink": "Copy-on-write folder",
            "folder": "Folder copy"
        }

        created_text = info.created_at

        try:
            created_text = (
                datetime.fromisoformat(info.created_at)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M")
            )
        except (TypeError, ValueError):
            pass

        self.backup_status_label.setText(
            f"Backup from {created_text} - "
            f"{method_labels.get(info.method, info.method)} - "
            f"{BackupManager.format_size(info.stored_size)} stored "
            f"({BackupManager.format_size(info.source_size)} original)"
        )

        self.backup_status_label.setToolTip(
            str(info.backup_path)
        )

        self._update_buttons()


    def _prefix_operation_is_blocked(self):

        if self.manager and self.manager.game_is_running(
            self.game.appid
        ):

            QMessageBox.warning(
                self,
                "Game is still running",
                (
                    "Close the game completely before backing up, "
                    "restoring, or modifying its Proton prefix."
                )
            )

            return True

        parent = self.parent()

        if (
            parent is not None
            and
            hasattr(parent, "_trainer_is_running")
            and
            parent._trainer_is_running()
        ):

            QMessageBox.warning(
                self,
                "Trainer is still running",
                (
                    "Close the trainer completely before backing up, "
                    "restoring, or modifying the Proton prefix."
                )
            )

            return True

        return False


    def _component_preview_text(
        self,
        component_names
    ):

        preview_names = component_names[:10]

        component_list = "\n".join(
            f"• {name}"
            for name in preview_names
        )

        if len(component_names) > len(preview_names):

            component_list += (
                "\n"
                f"• ...and {len(component_names) - len(preview_names)} more"
            )

        return component_list


    def _ask_backup_choice(
        self,
        component_names
    ):

        component_list = self._component_preview_text(
            component_names
        )

        message_box = QMessageBox(self)
        message_box.setIcon(QMessageBox.Icon.Warning)
        message_box.setWindowTitle("Modify Proton prefix")
        message_box.setText(
            "Installing components can permanently modify the Proton prefix."
        )
        message_box.setInformativeText(
            f"The following {len(component_names)} component(s) will be "
            f"installed for {self.game.name}:\n\n"
            f"{component_list}\n\n"
            "A complete safety backup is strongly recommended. It protects "
            "the registry, DLL overrides, runtimes, files, Proton metadata, "
            "and local saves stored inside compatdata.\n\n"
            "The game and its trainer must be completely closed."
        )

        remember_choice = QCheckBox(
            "Remember my choice"
        )
        message_box.setCheckBox(
            remember_choice
        )

        create_button = message_box.addButton(
            "Create Backup",
            QMessageBox.ButtonRole.AcceptRole
        )
        ignore_button = message_box.addButton(
            "Ignore && Continue",
            QMessageBox.ButtonRole.DestructiveRole
        )
        cancel_button = message_box.addButton(
            QMessageBox.StandardButton.Cancel
        )

        message_box.setDefaultButton(
            create_button
        )
        message_box.exec()

        clicked_button = message_box.clickedButton()

        if clicked_button is create_button:
            choice = "create"
        elif clicked_button is ignore_button:
            choice = "ignore"
        else:
            choice = "cancel"

        if remember_choice.isChecked():

            if choice == "create":

                self.settings.setValue(
                    BACKUP_POLICY_KEY,
                    BACKUP_POLICY_ALWAYS
                )

            elif choice == "ignore":

                self.settings.setValue(
                    BACKUP_POLICY_KEY,
                    BACKUP_POLICY_NEVER
                )

            self.settings.sync()

        del cancel_button
        return choice


    def _confirm_backup_replacement(self):

        if self.backup_manager.load_info() is None:
            return True

        answer = QMessageBox.warning(
            self,
            "Replace existing safety backup",
            (
                "A safety backup already exists for this game.\n\n"
                "Creating a new backup will replace the existing one only "
                "after the new backup has been completed successfully."
            ),
            (
                QMessageBox.StandardButton.Yes
                |
                QMessageBox.StandardButton.Cancel
            ),
            QMessageBox.StandardButton.Cancel
        )

        return answer == QMessageBox.StandardButton.Yes


    def _prepare_backup_for_installation(
        self,
        component_names
    ):

        if not self._confirm_backup_replacement():
            return

        try:

            windows_version = (
                self.manager.get_windows_version(
                    self.game.appid
                )
                if self.manager
                else None
            )

        except Exception:

            windows_version = None

        requested_method = str(
            self.settings.value(
                BACKUP_METHOD_KEY,
                BACKUP_METHOD_AUTO
            )
        )

        self.pending_install_components = tuple(
            component_names
        )

        self._start_backup_operation(
            action="create",
            requested_method=requested_method,
            components=component_names,
            windows_version=windows_version
        )


    def _start_backup_operation(
        self,
        action,
        requested_method=BACKUP_METHOD_AUTO,
        components=(),
        windows_version=None
    ):

        if self._is_busy():
            return

        if (
            action != "delete"
            and
            self._prefix_operation_is_blocked()
        ):
            return

        self.backup_action = action
        self.backup_result = None
        self.backup_error = None

        self.backup_thread = QThread(self)
        self.backup_worker = BackupWorker(
            backup_manager=self.backup_manager,
            action=action,
            requested_method=requested_method,
            components=components,
            windows_version=windows_version
        )

        self.backup_worker.moveToThread(
            self.backup_thread
        )

        self.backup_thread.started.connect(
            self.backup_worker.run
        )
        self.backup_worker.progress.connect(
            self._backup_progress
        )
        self.backup_worker.finished.connect(
            self._backup_operation_finished
        )
        self.backup_worker.failed.connect(
            self._backup_operation_failed
        )
        self.backup_worker.finished.connect(
            self.backup_thread.quit
        )
        self.backup_worker.failed.connect(
            self.backup_thread.quit
        )
        self.backup_worker.finished.connect(
            self.backup_worker.deleteLater
        )
        self.backup_worker.failed.connect(
            self.backup_worker.deleteLater
        )
        self.backup_thread.finished.connect(
            self._backup_thread_finished
        )

        action_messages = {
            "create": "Creating safety backup...",
            "restore": "Restoring safety backup...",
            "delete": "Deleting safety backup..."
        }

        self._set_busy(
            True,
            action_messages.get(
                action,
                "Processing safety backup..."
            )
        )

        if action == "delete":
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        self.cancel_operation_button.setVisible(
            action == "create"
        )
        self.cancel_operation_button.setEnabled(
            action == "create"
        )

        self.backup_thread.start()


    @Slot(object, object, str)
    def _backup_progress(
        self,
        processed,
        total,
        message
    ):

        try:
            processed_value = int(processed or 0)
            total_value = int(total or 0)
        except (TypeError, ValueError, OverflowError):
            processed_value = 0
            total_value = 0

        if total_value > 0:

            percentage = max(
                0,
                min(
                    100,
                    int(processed_value * 100 / total_value)
                )
            )

            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percentage)

            self.status_label.setText(
                f"{message} "
                f"{BackupManager.format_size(processed_value)} of "
                f"{BackupManager.format_size(total_value)}"
            )

        else:

            self.progress_bar.setRange(0, 0)
            self.status_label.setText(message)


    def _cancel_backup_operation(self):

        if (
            self.backup_action != "create"
            or
            self.backup_worker is None
        ):
            return

        self.cancel_operation_button.setEnabled(False)
        self.status_label.setText(
            "Cancelling safety backup..."
        )
        self.backup_worker.cancel()


    @Slot(object)
    def _backup_operation_finished(
        self,
        result
    ):

        self.backup_result = result


    @Slot(str)
    def _backup_operation_failed(
        self,
        message
    ):

        self.backup_error = message


    @Slot()
    def _backup_thread_finished(self):

        thread = self.backup_thread
        action = self.backup_action
        result = self.backup_result
        error = self.backup_error

        self.backup_thread = None
        self.backup_worker = None
        self.backup_action = None

        if thread:
            thread.deleteLater()

        self._set_busy(False)
        self._refresh_backup_status()

        if error:

            if "cancelled" in error.lower():

                self.pending_install_components = None
                self.status_label.setText(
                    "Safety backup cancelled. Component installation was not started."
                )

                return

            if action == "delete":
                self.status_label.setText(
                    "Safety backup deletion failed."
                )

                QMessageBox.critical(
                    self,
                    "Backup deletion failed",
                    error
                )

                if self.refresh_after_backup_delete:
                    self.refresh_after_backup_delete = False
                    QTimer.singleShot(
                        0,
                        lambda: self.load_components(force_refresh=False)
                    )

                return

            self.status_label.setText(
                "Safety backup operation failed."
            )

            if action == "create" and self.pending_install_components:

                message_box = QMessageBox(self)
                message_box.setIcon(QMessageBox.Icon.Warning)
                message_box.setWindowTitle("Safety backup failed")
                message_box.setText(
                    "The safety backup could not be created."
                )
                message_box.setInformativeText(
                    f"{error}\n\n"
                    "Continuing without a backup can leave the prefix "
                    "unrecoverable if the component installation changes "
                    "something unexpectedly."
                )

                ignore_button = message_box.addButton(
                    "Ignore && Continue",
                    QMessageBox.ButtonRole.DestructiveRole
                )
                message_box.addButton(
                    QMessageBox.StandardButton.Cancel
                )
                message_box.exec()

                pending_components = self.pending_install_components
                self.pending_install_components = None

                if message_box.clickedButton() is ignore_button:
                    self._start_installation(pending_components)

            else:

                QMessageBox.critical(
                    self,
                    "Safety backup failed",
                    error
                )

            return

        if action == "create":

            pending_components = self.pending_install_components
            self.pending_install_components = None

            self.status_label.setText(
                "Safety backup completed. Starting component installation..."
            )

            if pending_components:
                QTimer.singleShot(
                    0,
                    lambda names=pending_components: self._start_installation(
                        names
                    )
                )

        elif action == "restore":

            self.prefix_restored = True
            self.status_label.setText(
                "Safety backup restored successfully."
            )

            message_box = QMessageBox(self)
            message_box.setIcon(QMessageBox.Icon.Information)
            message_box.setWindowTitle("Backup restored")
            message_box.setText(
                "The complete Proton compatdata backup was restored "
                "successfully."
            )
            message_box.setInformativeText(
                "The safety backup is no longer required for this restore. "
                "Delete it now? Keeping it allows you to restore the same "
                "state again later."
            )

            delete_button = message_box.addButton(
                "Delete Backup",
                QMessageBox.ButtonRole.DestructiveRole
            )
            keep_button = message_box.addButton(
                "Keep Backup",
                QMessageBox.ButtonRole.RejectRole
            )
            message_box.setDefaultButton(keep_button)
            message_box.exec()

            if message_box.clickedButton() is delete_button:
                self.refresh_after_backup_delete = True
                QTimer.singleShot(
                    0,
                    lambda: self._start_backup_operation(
                        action="delete"
                    )
                )
            else:
                QTimer.singleShot(
                    0,
                    lambda: self.load_components(force_refresh=False)
                )

        elif action == "delete":

            self.status_label.setText(
                "Safety backup deleted."
            )

            if self.refresh_after_backup_delete:
                self.refresh_after_backup_delete = False
                QTimer.singleShot(
                    0,
                    lambda: self.load_components(force_refresh=False)
                )

        del result


    def restore_backup(self):

        info = self.backup_manager.load_info()

        if info is None or self._is_busy():
            return

        if self._prefix_operation_is_blocked():
            return

        answer = QMessageBox.warning(
            self,
            "Restore safety backup",
            (
                f"Restore the complete Proton compatdata backup for "
                f"{self.game.name}?\n\n"
                "All current prefix changes will be replaced by the backup. "
                "Local save files stored inside the prefix will also return "
                "to the backup state.\n\n"
                "The current compatdata directory is kept until the restored "
                "copy has been prepared and verified."
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

        self._start_backup_operation(
            action="restore"
        )


    def delete_backup(self):

        info = self.backup_manager.load_info()

        if info is None or self._is_busy():
            return

        answer = QMessageBox.warning(
            self,
            "Delete safety backup",
            (
                f"Permanently delete the safety backup for "
                f"{self.game.name}?\n\n"
                "This cannot be undone."
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

        self._start_backup_operation(
            action="delete"
        )


    def install_selected_components(self):

        component_names = self._checked_component_names()

        if not component_names:
            return

        if self._prefix_operation_is_blocked():
            return

        backup_policy = str(
            self.settings.value(
                BACKUP_POLICY_KEY,
                BACKUP_POLICY_ASK
            )
        )

        if backup_policy == BACKUP_POLICY_ALWAYS:

            self._prepare_backup_for_installation(
                component_names
            )

        elif backup_policy == BACKUP_POLICY_NEVER:

            self._start_installation(
                component_names
            )

        else:

            choice = self._ask_backup_choice(
                component_names
            )

            if choice == "create":

                self._prepare_backup_for_installation(
                    component_names
                )

            elif choice == "ignore":

                self._start_installation(
                    component_names
                )


    def _start_installation(
        self,
        component_names
    ):

        if self._is_busy():
            return

        self.output_field.clear()

        component_text = (
            component_names[0]
            if len(component_names) == 1
            else f"{len(component_names)} components"
        )

        self._set_busy(
            True,
            (
                f"Installing {component_text}. "
                "Watch for installer windows..."
            )
        )

        self.install_thread = QThread(self)

        self.install_worker = ComponentInstallWorker(
            manager=self.manager,
            appid=self.game.appid,
            component_names=component_names
        )

        self.install_worker.moveToThread(
            self.install_thread
        )

        self.install_thread.started.connect(
            self.install_worker.run
        )

        self.install_worker.finished.connect(
            self._installation_finished
        )

        self.install_worker.failed.connect(
            self._installation_failed
        )

        self.install_worker.finished.connect(
            self.install_thread.quit
        )

        self.install_worker.failed.connect(
            self.install_thread.quit
        )

        self.install_worker.finished.connect(
            self.install_worker.deleteLater
        )

        self.install_worker.failed.connect(
            self.install_worker.deleteLater
        )

        self.install_thread.finished.connect(
            self._install_thread_finished
        )

        self.install_thread.start()


    @Slot(str)
    def _installation_finished(
        self,
        output
    ):

        if output.strip():

            self.output_field.setPlainText(
                output[-12000:]
            )

        else:

            self.output_field.setPlainText(
                (
                    "Protontricks completed without "
                    "additional text output."
                )
            )

        self.status_label.setText(
            "Installation completed successfully."
        )

        self.reload_after_install = True

        QMessageBox.information(
            self,
            "Installation completed",
            (
                "Protontricks completed successfully. "
                "The installation status will now be refreshed."
            )
        )


    @Slot(str)
    def _installation_failed(
        self,
        message
    ):

        self.output_field.setPlainText(
            message
        )

        self._set_log_visible(
            True
        )

        self.status_label.setText(
            "Installation failed."
        )

        QMessageBox.critical(
            self,
            "Installation failed",
            message
        )


    @Slot()
    def _install_thread_finished(self):

        thread = self.install_thread

        self.install_thread = None
        self.install_worker = None

        if thread:
            thread.deleteLater()

        self._set_busy(
            False
        )

        if self.reload_after_install:

            self.reload_after_install = False

            QTimer.singleShot(
                0,
                lambda: self.load_components(
                    force_refresh=False
                )
            )


    def closeEvent(
        self,
        event
    ):

        if self._is_busy():

            QMessageBox.information(
                self,
                "Operation in progress",
                (
                    "Please wait until the current operation "
                    "has finished."
                )
            )

            event.ignore()
            return

        self._save_ui_state()

        super().closeEvent(event)
