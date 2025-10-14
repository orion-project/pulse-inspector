from utils import load_json

CMD_CONNECT = "CONNECT"
CMD_DISCONNECT = "DISCONNECT"

def get_cmd_status(name):
    if name == CMD_CONNECT:
      return "Connecting..."
    if name == CMD_DISCONNECT:
      return "Disconnecting..."
    return None

###########################################

class Command:
  def __init__(self, name, spec):
    self.name = name
    self.timeout = spec.get("timeout", 0)
    self.status = spec.get("status")
    if not self.status:
      self.status = get_cmd_status(name)

###########################################

class Protocol:
  data = {}

  def __init__(self, src):
    self.data = src if isinstance(src, dict) else load_json(src)

  def get_cmd(self, cmd) -> Command:
    spec = self.data.get("commands").get(cmd)
    if not spec:
      raise Exception(f"Command not found: {cmd}")
    return Command(cmd, spec)
