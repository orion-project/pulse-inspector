import serial
import serial.tools.list_ports
import time

from board import Board
from protocol import get_cmd_status, CMD_CONNECT, CMD_DISCONNECT
from utils import load_json

class SerialBoard(Board):
  config: dict = {}
  uart: serial.Serial = None

  def __init__(self):
    super().__init__("board_params.json")
    self.config = load_json("board_config.json")

  def port(self):
    port = self.config.get("port")
    if not port:
      ports = serial.tools.list_ports.comports()
      for p in ports:
        port = p.device
        break
    return port

  def loop(self):
    while True:
      time.sleep(0.001)
      try:
        if not self.cmd:
          continue

        print("Command: " + self.cmd)
        if self.cmd == CMD_CONNECT:
          self.on_status.emit(get_cmd_status(self.cmd))
          self._connect()
        elif self.cmd == CMD_DISCONNECT:
          self.on_status.emit(get_cmd_status(self.cmd))
          self._disconnect()

      except Exception as e:
        self.on_error.emit(self.cmd, str(e))
      finally:
        self.cmd = None

  def _connect(self):
    if self.uart:
      self.disconnect()
    port = self.port()
    baud_rate = self.protocol.data.get("baud_rate", 115200)
    timeout = self.config.get("timeout", 1)
    self.uart = serial.Serial(port, baud_rate, timeout=timeout)
    print(f"Connected to {port} at {baud_rate}")
    self.connected = True
    self.on_connect.emit()

  def _disconnect(self):
    if self.uart and self.uart.is_open:
      self.uart.close()
    self.uart = None
    self.connected = False
    self.on_connect.emit()
