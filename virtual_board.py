import logging
import time

from board import Board
from consts import CMD
from utils import make_sample_profile

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
          CMD.scan: { "timeout": 0.25 },
          CMD.scans: { "timeout": 0.25 },
        },
        "parameters": {
          "p1": {
            "title": "Simple parameter with very long title " +
              "(can hold any value, it is up to the formware how to parse it)"
          },
          "p2": {
            "title": "Integer parameter",
            "range": "10 - 100",
            "step": 10
          },
          "p3": {
            "title": "Float value",
            "range": "0 - 10.5",
            "precision": 4,
            "step": 0.5,
          },
          "p4": {
            "title": "Two options 0 and 1 are renderd as flag",
            "options": "0, 1",
          },
          "p5": {
            "title": "Selector",
            "options": "8, 16, 32, 64",
          }
        }
      }
    )
    self.params = {
      "p1": "Hello World",
      "p2": "42",
      "p3": "7",
      "p4": "1",
      "p5": "32"
    }

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
              if self._command_done():
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

  def _command_done(self) -> bool:
    if self._cmd == CMD.home:
      self.position = 0
      return True
    if self._cmd == CMD.move:
      self.position = self._cmd_args.get("pos", 0)
      return True
    if self._cmd == CMD.jog:
      if self.position is not None:
        self.position += self._cmd_args.get("offset", 0)
      return True
    if self._cmd == CMD.scan:
      self.on_data_received.emit(*make_sample_profile())
      return True
    if self._cmd == CMD.scans:
      self.on_data_received.emit(*make_sample_profile())
      self._cmd_start = time.perf_counter()
      return False
    return True

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
