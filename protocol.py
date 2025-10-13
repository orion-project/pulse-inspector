import json
import os

from utils import app_dir

CMD_CONNECT = "connect"
CMD_DISCONNECT = "disconnect"

###########################################

class Command:
  def __init__(self, spec):
    self.timeout = spec.get("timeout", 0)
    self.status = spec.get("status")

###########################################

class Protocol:
  _data = {}

  def __init__(self, file_name):

    fn = app_dir(file_name)
    if not os.path.exists(fn):
      raise Exception(f"File not found: {fn}")
    with open(fn, 'r') as f:
      try:
        self._data = json.load(f)
      except Exception as e:
        raise Exception(f"Failed to parse protocol file {fn}: {e}")

  def get_cmd(self, cmd) -> Command:
    cmd_spec = self._data.get("cmd").get(cmd)
    if not cmd_spec:
      raise Exception(f"Command not found: {cmd}")
    return Command(cmd_spec)
