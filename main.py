import sys
import argparse
import logging
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from consts import APP_NAME
from utils import load_icon

def main():
  logging.basicConfig(level=logging.DEBUG)
  log = logging.getLogger(__name__)

  parser = argparse.ArgumentParser(description=APP_NAME)
  parser.add_argument('--dev', action='store_true', help='Enable development mode')
  parser.add_argument('--virtual', action='store_true', help='Use virtual board')
  parser.add_argument('--config', help='Board config file name')
  parser.add_argument('--scan', help='Previously saved scan file to plot the profile from')
  args = parser.parse_args()

  app = QApplication(sys.argv)
  app.setStyle("fusion")
  app.setWindowIcon(load_icon("main.png"))
  app.setStyleSheet("QWidget { font-size: 15px }")
  app.styleHints().setColorScheme(Qt.ColorScheme.Light)

  try:
    if args.virtual:
      from virtual_board import VirtualBoard
      VirtualBoard()
    else:
      from serial_board import SerialBoard
      config_file: str = args.config
      if not config_file:
        config_file = "board_config.ini"
      SerialBoard(config_file)
  except Exception as e:
    log.exception("Error board initialization")
    QMessageBox.critical(None, APP_NAME, f"Error board initialization: {e}")
    sys.exit(1)

  # Import MainWindow after the board gets initialized
  from main_window import MainWindow
  window = MainWindow(dev_mode=args.dev, scan_file=args.scan)
  window.show()
  sys.exit(app.exec())

if __name__ == "__main__":
    main()
