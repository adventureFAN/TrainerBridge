import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout


class ProtonTrainerManager(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Proton Trainer Manager")
        self.resize(500, 300)

        layout = QVBoxLayout()

        text = QLabel("Proton Trainer Manager\n\nVersion 0.1")
        layout.addWidget(text)

        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = ProtonTrainerManager()
    window.show()

    sys.exit(app.exec())
