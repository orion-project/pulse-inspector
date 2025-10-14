import time

from board import Board
from protocol import CMD_CONNECT, CMD_DISCONNECT

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

        print("Command: " + self.cmd)
        cmd = self.protocol.get_cmd(self.cmd)
        if cmd.status:
          self.on_status.emit(cmd.status)
        if cmd.timeout > 0:
          time.sleep(cmd.timeout)
        if cmd.status:
          self.on_status.emit(None)
        if self.cmd == CMD_CONNECT:
          self.connected = True
          self.on_connect.emit()
        elif self.cmd == CMD_DISCONNECT:
          self.connected = False
          self.on_connect.emit()

      except Exception as e:
        self.on_error.emit(self.cmd, str(e))
      finally:
        self.cmd = None

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    print("[Debug] Connection interrupt")
    self.connected = False
    self.on_error.emit("Connection interrupted")
    self.on_connect.emit()
