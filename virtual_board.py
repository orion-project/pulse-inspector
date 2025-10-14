import logging
import time

from board import Board
from consts import CMD_CONNECT, CMD_DISCONNECT

log = logging.getLogger(__name__)

class VirtualBoard(Board):
  virtual = True

  def __init__(self):
    super().__init__(\
      {
        "commands": {
          CMD_CONNECT: {
            "timeout": 3
          },
          CMD_DISCONNECT: {
            "timeout": 3
          }
        }
      }
    )

  def port(self):
    return "VIRTUAL"

  def loop(self):
    while True:
      time.sleep(0.001)
      try:
        if not self.cmd:
          continue

        log.info("Command: " + self.cmd)
        cmd = self.config.get_cmd(self.cmd)
        if cmd.status:
          self.on_status.emit(cmd.status)
        if cmd.timeout > 0:
          time.sleep(cmd.timeout)
        if cmd.status:
          self.on_status.emit(None)
        if self.cmd == CMD_CONNECT:
          log.info("Connected")
          self.connected = True
          self.on_connect.emit()
        elif self.cmd == CMD_DISCONNECT:
          log.info("Disconnected")
          self.connected = False
          self.on_connect.emit()

      except Exception as e:
        log.exception(f"Failed to process command {self.cmd}")
        self.on_error.emit(str(e))
      finally:
        self.cmd = None

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    log.info("Force connection interrupt")
    self.connected = False
    self.on_error.emit("Connection interrupted")
    self.on_connect.emit()
