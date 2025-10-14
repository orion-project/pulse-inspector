import threading

from PySide6.QtCore import QObject, Signal

from config import Config
from consts import CMD_CONNECT, CMD_DISCONNECT

class Board(QObject):
  on_command_beg = Signal(str)
  on_command_end = Signal(str, str)

  connected = False
  cmd = None

  def __init__(self, config_file: str):
    super().__init__()

    self.config = Config(config_file)

    self.thread = threading.Thread(target=self.loop, daemon=True)
    self.thread.start()

  def toggle_connection(self):
    if self.connected:
      self.cmd = CMD_DISCONNECT
    else:
      self.cmd = CMD_CONNECT
