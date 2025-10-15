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

      self._lock.acquire()
      next_cmd = self._next_cmd
      cancel = self._cancel_cmd
      self._lock.release()

      try:
        # A command in progress
        if self._cmd_start > 0:
          # There are some commands that can cancel
          # other commands without finishing them
          if cancel:
            log.info(f"cancel:{self._cmd}")
          else:
            elapsed = time.perf_counter() - self._cmd_start
            if elapsed >= self._cmd_timeout:
              raise TimeoutError("Command timeout")
            continue

        if next_cmd:
          self._lock.acquire()
          self._next_cmd = None
          self._cancel_cmd = False
          self._lock.release()

          self._cmd = next_cmd
          log.info(f"begin:{self._cmd}")
          if self._cmd == CMD_CONNECT:
            self.on_command_beg.emit(self._cmd)
            self._connect()
            self._end_command(log, None)
          elif self._cmd == CMD_DISCONNECT:
            self.on_command_beg.emit(self._cmd)
            self._disconnect()
            self._end_command(log, None)
          else:
            cmd = self.config.cmd_spec(self._cmd)
            self.on_command_beg.emit(self._cmd)
            self._cmd_start = time.perf_counter()
            self._cmd_timeout = cmd.timeout

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(log, str(e))

  def _connect(self):
    if self.uart:
      self._disconnect()
    port = self.port()
    baudrate = self.config.value("connection/baudrate")
    timeout = self.config.value("connection/timeout")
    self.uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    log.info(f"Connected to {port} at {baudrate}")

  def _disconnect(self):
    if self.uart and self.uart.is_open:
      self.uart.close()
    self.uart = None
    log.info(f"Disconnected {self.port()}")
