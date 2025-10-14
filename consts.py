APP_NAME = "Pulse Inspector"
APP_VERSION = "0.0.1"

CMD_CONNECT = "CONNECT"
CMD_DISCONNECT = "DISCONNECT"
CMD_HOME = "HOME"
CMD_STOP = "STOP"

def get_cmd_run_text(cmd):
  if cmd == CMD_CONNECT:
    return "Connecting..."
  if cmd == CMD_DISCONNECT:
    return "Disconnecting..."
  if cmd == CMD_HOME:
    return "Homing..."
  if cmd == CMD_STOP:
    return "Stopping..."
  return cmd.title() + "..."
