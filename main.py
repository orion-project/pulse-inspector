import sys

from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from utils import load_icon

def main():
    app = QApplication(sys.argv)
    app.setStyle("fusion")
    app.setWindowIcon(load_icon("main.png"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
