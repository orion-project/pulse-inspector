import sys
import argparse

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from consts import APP_NAME
from main_window import MainWindow
from utils import load_icon

def main():
  parser = argparse.ArgumentParser(description=APP_NAME)
  parser.add_argument('--dev', action='store_true', help='Enable development mode')
  parser.add_argument('--virtual', action='store_true', help='Use virtual board')
  args = parser.parse_args()

  app = QApplication(sys.argv)
  app.setStyle("fusion")
  app.setWindowIcon(load_icon("main.png"))
  app.setStyleSheet("QWidget { font-size: 14px }")

  board = None
  try:
    if args.virtual:
      from virtual_board import VirtualBoard
      board = VirtualBoard()
    else:
      from serial_board import SerialBoard
      board = SerialBoard()
  except Exception as e:
    print(f"Error board initialization: {e}")
    QMessageBox.critical(None, APP_NAME, f"Error board initialization: {e}")
    sys.exit(1)

  window = MainWindow(board, dev_mode=args.dev)
  window.show()
  sys.exit(app.exec())

if __name__ == "__main__":
    main()
