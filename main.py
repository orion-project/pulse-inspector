import sys
import argparse
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from consts import APP_NAME
from main_window import MainWindow
from utils import load_icon

def main():
  logging.basicConfig(level=logging.DEBUG)
  log = logging.getLogger(__name__)

  parser = argparse.ArgumentParser(description=APP_NAME)
  parser.add_argument('--dev', action='store_true', help='Enable development mode')
  parser.add_argument('--virtual', action='store_true', help='Use virtual board')
  args = parser.parse_args()

  app = QApplication(sys.argv)
  app.setStyle("fusion")
  app.setWindowIcon(load_icon("main.png"))
  app.setStyleSheet("QWidget { font-size: 15px }")
  app.styleHints().setColorScheme(Qt.ColorScheme.Light)

  board = None
  try:
    if args.virtual:
      from virtual_board import VirtualBoard
      board = VirtualBoard()
    else:
      from serial_board import SerialBoard
      board = SerialBoard()
  except Exception as e:
    log.exception("Error board initialization")
    QMessageBox.critical(None, APP_NAME, f"Error board initialization: {e.__class__}: {e}")
    sys.exit(1)

  window = MainWindow(board, dev_mode=args.dev)
  window.show()
  sys.exit(app.exec())

if __name__ == "__main__":
    main()
