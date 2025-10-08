from PySide6.QtWidgets import QMainWindow, QLabel

from consts import APP_NAME, APP_VERSION

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
