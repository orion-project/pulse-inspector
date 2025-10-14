import serial
import serial.tools.list_ports
import time
import logging

from board import Board
from consts import CMD_CONNECT, CMD_DISCONNECT

log = logging.getLogger(__name__)

class SerialBoard(Board):
  uart: serial.Serial = None

  def __init__(self):
    super().__init__("board_config.ini")

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
        self.on_command_beg.emit(self.cmd)
        if self.cmd == CMD_CONNECT:
          self._connect()
        elif self.cmd == CMD_DISCONNECT:
          self._disconnect()
        self.on_command_end.emit(self.cmd, None)

      except Exception as e:
        log.exception(f"Failed to process command {self.cmd}")
        self.on_command_end.emit(self.cmd, str(e))
      finally:
        self.cmd = None

  def _connect(self):
    if self.uart:
      self.disconnect()
    port = self.port()
    baudrate = self.config.value("connection/baudrate")
    timeout = self.config.value("connection/timeout")
    self.uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    self.connected = True
    log.info(f"Connected to {port} at {baudrate}")

  def _disconnect(self):
    if self.uart and self.uart.is_open:
      self.uart.close()
    self.uart = None
    self.connected = False
    log.info(f"Disconnected {self.port()}")
