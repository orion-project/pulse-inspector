from enum import Enum

APP_NAME = "Pulse Inspector"
APP_VERSION = "0.0.1"
APP_PAGE = "https://github.com/orion-project/pulse-inspector"

class CMD(Enum):
  connect = "CONNECT"
  disconnect = "DISCONNECT"
  home = "HOME"
  stop = "STOP"
  move = "MOVE"
  jog = "JOG"
  error = "ERROR"

def get_cmd_run_text(cmd: CMD) -> str:
  if cmd == CMD.connect:
    return "Connecting..."
  if cmd == CMD.disconnect:
    return "Disconnecting..."
  if cmd == CMD.home:
    return "Homing..."
  if cmd == CMD.stop:
    return "Stopping..."
  if cmd == CMD.move or cmd == CMD.jog:
    return "Moving..."
  return cmd.value.title() + "..."
