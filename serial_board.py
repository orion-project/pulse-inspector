import serial
import serial.tools.list_ports
import time
import logging

from board import Board
from consts import CMD

log = logging.getLogger(__name__)

class SerialBoard(Board):
  uart: serial.Serial = None

  def __init__(self):
    super().__init__(log, "board_config.ini")

  def port(self):
    port = self.config.value("connection/port")
    if not port:
      ports = serial.tools.list_ports.comports()
      for p in ports:
        port = p.device
        break
    return port

  def loop(self):
    answer_ok = self.config.value("commands/answer_ok")
    answer_err = self.config.value("commands/answer_err")

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
            ans = self.uart.readline().decode('utf-8').strip()
            if ans:
              log.debug(f"receive:{ans}")
              if ans.startswith(answer_ok):
                self._command_done(ans)
                self._end_command(None)
              elif ans.startswith(answer_err):
                self._end_command(self.config.error_text(ans))
            continue

        if next_cmd:
          self._lock.acquire()
          self._next_cmd = None
          self._cancel_cmd = False
          self._lock.release()

          self._cmd = next_cmd
          log.info(f"begin:{self._cmd}")
          if self._cmd == CMD.connect:
            self.on_command_beg.emit(self._cmd)
            self._connect()
            self._end_command(None)
          elif self._cmd == CMD.disconnect:
            self.on_command_beg.emit(self._cmd)
            self._disconnect()
            self._end_command(None)
          else:
            cmd = self.config.cmd_spec(self._cmd.value)
            if not cmd.serial_name:
              raise Exception(f"Command serial name is empty")
            self.on_command_beg.emit(self._cmd)
            self._cmd_start = time.perf_counter()
            self._cmd_timeout = cmd.timeout
            serial_cmd = cmd.serial_name + self._command_args()
            log.debug(f"send:{serial_cmd}")
            self.uart.write(serial_cmd.encode())
            self.uart.flush()

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(str(e))

  def _connect(self):
    if self.uart:
      self._disconnect()
    port = self.port()
    baudrate = self.config.value("connection/baudrate")
    timeout = self.config.value("connection/timeout")
    self.uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    # Arduino boards reset when a serial connection is opened
    # Delay after connection allows it to complete its bootloader and initialization sequence
    time.sleep(self.config.value("connection/reset_time", 2))
    self.uart.reset_input_buffer()
    self.uart.reset_output_buffer()
    log.info(f"Connected to {port} at {baudrate}")

  def _disconnect(self):
    if self.uart and self.uart.is_open:
      self.uart.close()
    self.uart = None
    log.info(f"Disconnected {self.port()}")

  def _command_args(self) -> str:
    if self._cmd == CMD.move:
      return f" {self._cmd_args.get("pos", 0)}"
    if self._cmd == CMD.jog:
      return f" {self._cmd_args.get("offset", 0)}"
    return ""

  def _command_done(self, ans: str):
    if self._cmd == CMD.home or self._cmd == CMD.move or self._cmd == CMD.jog:
      res = ans.split(" ")
      if len(res) > 1:
        self.position = float(res[-1])

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    self.uart.close()

  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._next_cmd = CMD.error
    self._cancel_cmd = True
