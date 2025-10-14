APP_NAME = "Pulse Inspector"
APP_VERSION = "0.0.1"

CMD_CONNECT = "CONNECT"
CMD_DISCONNECT = "DISCONNECT"

def get_cmd_status(name):
  if name == CMD_CONNECT:
    return "Connecting..."
  if name == CMD_DISCONNECT:
    return "Disconnecting..."
  return None

def get_cmd_run_text(cmd):
  if cmd == CMD_CONNECT:
    return "Connecting..."
  if cmd == CMD_DISCONNECT:
    return "Disconnecting..."
  return cmd.title() + "..."
