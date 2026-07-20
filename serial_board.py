import time
import logging
import serial
import serial.tools.list_ports
from typing import override

from config import Config
from board import Board
from consts import CMD

log = logging.getLogger(__name__)

class SerialBoard(Board):
  _uart: serial.Serial|None = None
  _profile_x = []
  _profile_y = []
  _cmd_log_answer = True

  def __init__(self, config_file: str):
    super().__init__(log, Config(config_file))

  @override
  def port(self) -> str:
    port = self.config.value(str, "connection/port", '')
    if not port:
      ports = serial.tools.list_ports.comports()
      for p in ports:
        port = p.device
        break
    return port

  @override
  def loop(self):
    answer_ok = self.config.value(str, "commands/answer_ok", None)
    answer_error = self.config.value(str, "commands/answer_error", None)

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
          # They will be finished when we receive OK after the STOP command
          if cancel:
            log.info(f"cancel:{self._cmd}")
          else:
            elapsed = time.perf_counter() - self._cmd_start
            if elapsed >= self._cmd_timeout:
              raise TimeoutError("Command timeout")
            if self._uart:
              ans = self._uart.readline().decode('utf-8').strip()
              if ans:
                if ans.startswith(answer_ok):
                  if self._cmd_log_answer:
                    log.debug(f"receive:{ans}")
                  if self._command_done(ans):
                    self._end_command(None)
                elif ans.startswith(answer_error):
                  log.debug(f"receive:{ans}")
                  self._end_command(self.config.error_text(ans))
                else: # Some debug output from the board
                  if self._cmd_log_answer:
                    log.debug(f"receive:{ans}")
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
            self._run_command(True)

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(str(e))

  def _run_command(self, emit_beg_signal: bool):
    if self._uart and self._cmd:
      cmd = self.config.cmd_spec(self._cmd.value)
      if not cmd.serial_name:
        raise Exception(f"Command serial name is empty")
      cmd_args = self._prepare_command()
      serial_cmd = f"{cmd.serial_name} {cmd_args}".strip()
      if emit_beg_signal:
        self.on_command_beg.emit(self._cmd)
      self._cmd_start = time.perf_counter()
      self._cmd_timeout = cmd.timeout
      self._cmd_log_answer = cmd.log_answer
      log.debug(f"send:{serial_cmd}")
      self._uart.write(serial_cmd.encode())
      self._uart.flush()

  def _connect(self):
    if self._uart:
      self._disconnect()
    port = self.port()
    baudrate = self.config.value(int, "connection/baudrate", None)
    timeout = self.config.value(float, "connection/timeout", None)
    self._uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    # Arduino boards reset when a serial connection is opened
    # Delay after connection allows it to complete its bootloader and initialization sequence
    time.sleep(self.config.value(float, "connection/reset_time", 2))
    self._uart.reset_input_buffer()
    self._uart.reset_output_buffer()
    log.info(f"Connected to {port} at {baudrate}")

  def _disconnect(self):
    if self._uart and self._uart.is_open:
      self._uart.close()
    self._uart = None
    log.info(f"Disconnected {self.port()}")

  def _prepare_command(self):
    # Do some stuff before command start and return command arguments
    if self._cmd == CMD.move:
      return self._cmd_args.get("pos", 0)

    if self._cmd == CMD.jog:
      offset = self._cmd_args.get("offset", 0)
      microstep = "1" if self._microstep_jog else "0"
      return f"{offset} {microstep}"

    if self._cmd == CMD.scan or self._cmd == CMD.scans:
      self._profile_x = []
      self._profile_y = []

    if self._cmd == CMD.param:
      if self._cmd_args.get("store"):
        params: list[tuple[str, str]] = self._cmd_args["params"]
        name, value = params[0]
        log.info(f"store_param:{name}={value}")
        return f"{name} {value}"

    if self._cmd == CMD.scan or self._cmd == CMD.scans:
      if self._scan_range is not None:
        return str(self._scan_range)

    return ""

  def _command_done(self, ans: str):
    if self._cmd == CMD.home or self._cmd == CMD.move or self._cmd == CMD.jog:
      res = ans.split(" ")
      if len(res) > 2:
        raise Exception(f"Unexpected command result: '{res}' ")
      if len(res) == 2: # e.g. `OK 0.5`
        self.position = float(res[-1])
      return True

    if self._cmd == CMD.scan or self._cmd == CMD.scans:
      res = ans.split(" ")
      if len(res) == 1:
        # End of continuous scan loop, `OK`
        #log.debug(f"data_received:continuous:len={len(self._profile_x)}")
        self.on_data_received.emit(self._profile_x, self._profile_y)
        self._profile_x = []
        self._profile_y = []
        return False # Continue to the next loop
      if len(res) == 2:
        # End of single scan loop, e.g. `OK 100`
        self.position = float(res[-1])
        self.on_stage_moved.emit()
        #log.debug(f"data_received:single:len={len(self._profile_x)}")
        self.on_data_received.emit(self._profile_x, self._profile_y)
        return True
      if len(res) == 3:
        # Next scan point received, e.g. `OK 0.70 911.82`
        self.position = float(res[-2])
        self.level = float(res[-1])
        self._profile_x.append(self.position)
        self._profile_y.append(self.level)
        self.on_stage_moved.emit()
        self._cmd_start = time.perf_counter()
        return False # Continue scanning
      raise Exception(f"Unexpected command result: '{res}' ")

    if self._cmd == CMD.param:
      if self._cmd_args.get("store"):
        # Store params
        params: list[tuple[str, str]] = self._cmd_args["params"]
        (name, value) = params[0]
        log.info(f"param_stored:{name}={value}")
        params = params[1:]
        if not params:
          return True
        self._cmd_args["params"] = params
        self._run_command(False)
        return False
      else:
        # Receive params
        res = ans.split(" ")
        if len(res) == 1:
          return True
        if len(res) == 3:
          self.params[res[1]] = res[2]
          self._cmd_start = time.perf_counter()
          return False
        raise Exception("Unexpected command result")
    return True

  @override
  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    if self._uart:
      self._uart.close()

  @override
  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._next_cmd = CMD.error
    self._cancel_cmd = True
