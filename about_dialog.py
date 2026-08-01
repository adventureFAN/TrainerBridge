from PySide6.QtCore import (
    Qt,
    QUrl
)

from PySide6.QtGui import (
    QDesktopServices,
    QPixmap
)

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout
)

from core.paths import LOG_DIR
from core.resources import resource_path
from core.version import (
    APP_DESCRIPTION,
    APP_DISPLAY_VERSION,
    APP_NAME,
    AUTHOR_NAME,
    PROJECT_URL
)


class AboutDialog(QDialog):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)

        self.setWindowTitle(
            f"About {APP_NAME}"
        )

        self.setFixedWidth(
            520
        )

        self._build_interface()


    def _build_interface(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            28,
            24,
            28,
            24
        )

        layout.setSpacing(
            14
        )

        icon_label = QLabel()

        icon_pixmap = QPixmap(
            str(
                resource_path(
                    "assets/trainerbridge.png"
                )
            )
        )

        if not icon_pixmap.isNull():

            icon_label.setPixmap(
                icon_pixmap.scaled(
                    112,
                    112,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title_label = QLabel(
            APP_NAME
        )

        title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        title_label.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        version_label = QLabel(
            f"Version {APP_DISPLAY_VERSION}"
        )

        version_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        description_label = QLabel(
            APP_DESCRIPTION
        )

        description_label.setWordWrap(
            True
        )

        description_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        beta_label = QLabel(
            "Beta software — please report unexpected behavior."
        )

        beta_label.setWordWrap(
            True
        )

        beta_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        beta_label.setStyleSheet(
            "font-style: italic; color: gray;"
        )

        author_label = QLabel(
            f"Developed by {AUTHOR_NAME}"
        )

        author_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(version_label)
        layout.addWidget(description_label)
        layout.addWidget(beta_label)
        layout.addWidget(author_label)

        button_layout = QHBoxLayout()

        if PROJECT_URL:

            project_button = QPushButton(
                "Project Page"
            )

            project_button.clicked.connect(
                self._open_project_page
            )

            button_layout.addWidget(
                project_button
            )

        log_button = QPushButton(
            "Open Log Folder"
        )

        log_button.clicked.connect(
            self._open_log_folder
        )

        notices_button = QPushButton(
            "Third-Party Notices"
        )

        notices_button.clicked.connect(
            self._show_third_party_notices
        )

        close_button = QPushButton(
            "Close"
        )

        close_button.clicked.connect(
            self.accept
        )

        button_layout.addWidget(log_button)
        button_layout.addWidget(notices_button)
        button_layout.addStretch(1)
        button_layout.addWidget(close_button)

        layout.addLayout(
            button_layout
        )


    def _open_project_page(self):

        QDesktopServices.openUrl(
            QUrl(PROJECT_URL)
        )


    def _open_log_folder(self):

        LOG_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(LOG_DIR)
            )
        )


    def _show_third_party_notices(self):

        notices_path = resource_path(
            "assets/THIRD_PARTY_NOTICES.txt"
        )

        try:

            text = notices_path.read_text(
                encoding="utf-8"
            )

        except OSError as error:

            text = (
                "The notices file could not be opened.\n\n"
                f"{error}"
            )

        message_box = QMessageBox(self)

        message_box.setWindowTitle(
            "Third-Party Notices"
        )

        message_box.setIcon(
            QMessageBox.Icon.Information
        )

        message_box.setText(
            "TrainerBridge uses third-party software."
        )

        message_box.setDetailedText(
            text
        )

        message_box.exec()
