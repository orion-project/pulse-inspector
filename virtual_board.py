import logging
import time

from board import Board
from consts import CMD_CONNECT, CMD_DISCONNECT, CMD_HOME, CMD_STOP

log = logging.getLogger(__name__)

class VirtualBoard(Board):
  _cmd_error = None

  def __init__(self):
    super().__init__(\
      {
        "commands": {
          CMD_CONNECT: { "timeout": 0.5 },
          CMD_DISCONNECT: { "timeout": 0.5 },
          CMD_HOME: { "timeout": 5 },
          CMD_STOP: { "timeout": 0.5 }
        }
      }
    )

  def port(self):
    return "VIRTUAL"

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
              self._end_command(log, None)
            continue

        if self._cmd_error:
          err = self._cmd_error
          self._cmd_error = None
          raise Exception(err)

        if next_cmd:
          self._lock.acquire()
          self._next_cmd = None
          self._cancel_cmd = False
          self._lock.release()

          self._cmd = next_cmd
          log.info(f"begin:{self._cmd}")
          cmd = self.config.cmd_spec(self._cmd)
          self.on_command_beg.emit(self._cmd)
          self._cmd_start = time.perf_counter()
          self._cmd_timeout = cmd.timeout

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(log, str(e))

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    self._cmd = CMD_DISCONNECT
    self._cmd_error = "Connection interrupted"
    self._cancel_cmd = True

  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._cmd_error = "Something did not go"
    self._cancel_cmd = True
