import logging
import time

from board import Board
from consts import CMD

log = logging.getLogger(__name__)

class VirtualBoard(Board):
  _cmd_error = None

  def __init__(self):
    super().__init__(log, \
      {
        "commands": {
          CMD.connect: { "timeout": 0.5 },
          CMD.disconnect: { "timeout": 0.5 },
          CMD.home: { "timeout": 2 },
          CMD.stop: { "timeout": 0.5 },
          CMD.move: { "timeout": 2 },
          CMD.jog: { "timeout": 0.5 },
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
              self._command_done()
              self._end_command(None)
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
        self._end_command(str(e))

  def _command_done(self):
    if self._cmd == CMD.home:
      self.position = 0
    elif self._cmd == CMD.move:
      self.position = self._cmd_args.get("pos", 0)
    elif self._cmd == CMD.jog:
      if self.position is not None:
        self.position += self._cmd_args.get("offset", 0)

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    self._cmd = CMD.disconnect
    self._cmd_error = "Connection interrupted"
    self._cancel_cmd = True

  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._cmd_error = "Something did not go"
    self._cancel_cmd = True
