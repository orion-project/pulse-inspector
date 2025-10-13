import threading
import time

from PySide6.QtCore import QObject, Signal

from protocol import Protocol, CMD_CONNECT, CMD_DISCONNECT

class Board(QObject):
  on_status = Signal(str)
  on_error = Signal(str)
  on_connect = Signal()

  connected = False

  _cmd = None
  _protocol = Protocol("virtual_board.json")

  def __init__(self):
    super().__init__()

    self.thread = threading.Thread(target=self._loop, daemon=True)
    self.thread.start()

  def port(self):
    return "VIRTUAL"

  def toggle_connection(self):
    if self.connected:
      self._cmd = CMD_DISCONNECT
    else:
      self._cmd = CMD_CONNECT

  def _loop(self):
    while True:
      time.sleep(0.001)
      try:
        if not self._cmd:
          continue

        cmd = self._protocol.get_cmd(self._cmd)
        if cmd.status:
          self.on_status.emit(cmd.status)
        if cmd.timeout > 0:
          time.sleep(cmd.timeout)
        if cmd.status:
          self.on_status.emit(None)
        if self._cmd == CMD_CONNECT:
          self.connected = True
          self.on_connect.emit()
        elif self._cmd == CMD_DISCONNECT:
          self.connected = False
          self.on_connect.emit()

        self._cmd = None

      except Exception as e:
        self._cmd = None
        self.on_error.emit(str(e))

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    print("[Debug] Connection interrupt")
    self.connected = False
    self.on_error.emit("Connection interrupted")
    self.on_connect.emit()
