import serial
import serial.tools.list_ports
import time
import logging

from board import Board, CMD_CONNECT, CMD_DISCONNECT, get_cmd_status

log = logging.getLogger(__name__)

class SerialBoard(Board):
  uart: serial.Serial = None

  def __init__(self):
    super().__init__("board_config.json")

  def port(self):
    port = self.config.value("connection/port")
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

        log.info("Command: " + self.cmd)
        if self.cmd == CMD_CONNECT:
          self.on_status.emit(get_cmd_status(self.cmd))
          self._connect()
        elif self.cmd == CMD_DISCONNECT:
          self.on_status.emit(get_cmd_status(self.cmd))
          self._disconnect()

      except Exception as e:
        log.exception(f"Failed to process command {self.cmd}")
        self.on_error.emit(str(e))
      finally:
        self.cmd = None

  def _connect(self):
    if self.uart:
      self.disconnect()
    port = self.port()
    baudrate = self.config.value("connection/baudrate")
    timeout = self.config.value("connection/timeout")
    self.uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    log.info(f"Connected to {port} at {baudrate}")
    self.connected = True
    self.on_connect.emit()

  def _disconnect(self):
    if self.uart and self.uart.is_open:
      self.uart.close()
    self.uart = None
    self.connected = False
    self.on_connect.emit()
