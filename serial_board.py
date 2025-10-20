import time
import logging
import serial
import serial.tools.list_ports

from board import Board
from consts import CMD

log = logging.getLogger(__name__)

class SerialBoard(Board):
  _uart: serial.Serial = None
  _profile_x = []
  _profile_y = []
  _cmd_log_answer = True

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
    answer_error = self.config.value("commands/answer_error")

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
            cmd = self.config.cmd_spec(self._cmd.value)
            if not cmd.serial_name:
              raise Exception(f"Command serial name is empty")
            cmd_args = self._prepare_command()
            serial_cmd = f"{cmd.serial_name} {cmd_args}".strip()
            self.on_command_beg.emit(self._cmd)
            self._cmd_start = time.perf_counter()
            self._cmd_timeout = cmd.timeout
            self._cmd_log_answer = cmd.log_answer
            log.debug(f"send:{serial_cmd}")
            self._uart.write(serial_cmd.encode())
            self._uart.flush()

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(str(e))

  def _connect(self):
    if self._uart:
      self._disconnect()
    port = self.port()
    baudrate = self.config.value("connection/baudrate")
    timeout = self.config.value("connection/timeout")
    self._uart = serial.Serial(port, baudrate=baudrate, timeout=timeout)
    # Arduino boards reset when a serial connection is opened
    # Delay after connection allows it to complete its bootloader and initialization sequence
    time.sleep(self.config.value("connection/reset_time", 2))
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
      return self._cmd_args.get("offset", 0)

    if self._cmd == CMD.scan or self._cmd == CMD.scans:
      self._profile_x = []
      self._profile_y = []

    if self._cmd == CMD.param:
      if self._cmd_args.get("store"):
        params = self._cmd_args["params"]
        name = [*params][0]
        value = params[name]
        return f"{name} {value}"

    return ""

  def _command_done(self, ans: str):
    if self._cmd == CMD.home or self._cmd == CMD.move or self._cmd == CMD.jog:
      res = ans.split(" ")
      if len(res) > 2:
        raise Exception("Unexpected command result")
      if len(res) == 2: # e.g. `OK 0.5`
        self.position = float(res[-1])
      return True

    if self._cmd == CMD.scan or self._cmd == CMD.scans:
      res = ans.split(" ")
      if len(res) == 1:
        self.on_data_received.emit(self._profile_x, self._profile_y)
        self._profile_x = []
        self._profile_y = []
        # Finish only if the single scan, continue otherwise
        return self._cmd == CMD.scan
      if len(res) == 3: # e.g. `OK 0.70 911.82`
        self.position = float(res[-2])
        self._profile_x.append(self.position)
        self._profile_y.append(float(res[-1]))
        self.on_stage_moved.emit()
        self._cmd_start = time.perf_counter()
        return False # Continue scanning
      raise Exception("Unexpected command result")

    if self._cmd == CMD.param:
      if self._cmd_args.get("store"):
        # Store params
        params = self._cmd_args["params"]
        name = [*params][0]
        value = params[name]
        log.info(f"param_stored:{name}={value}")
        del params[name]
        self.on_param_stored.emit(len(params) > 0)
        return True
      else:
        # Receive params
        res = ans.split(" ")
        if len(res) == 1:
          self.on_params_received.emit()
          return True
        if len(res) == 3:
          self.params[res[1]] = res[2]
          return False
        raise Exception("Unexpected command result")
    return True

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    self._uart.close()

  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._next_cmd = CMD.error
    self._cancel_cmd = True
