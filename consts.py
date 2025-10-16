from enum import Enum

APP_NAME = "Pulse Inspector"
APP_VERSION = "0.0.1"

class CMD(Enum):
  connect = "CONNECT"
  disconnect = "DISCONNECT"
  home = "HOME"
  stop = "STOP"
  error = "ERROR"
  move = "MOVE"

def get_cmd_run_text(cmd: CMD) -> str:
  if cmd == CMD.connect:
    return "Connecting..."
  if cmd == CMD.disconnect:
    return "Disconnecting..."
  if cmd == CMD.home:
    return "Homing..."
  if cmd == CMD.stop:
    return "Stopping..."
  if cmd == CMD.move:
    return "Moving..."
  return cmd.value.title() + "..."
