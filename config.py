from configobj import ConfigObj

from consts import get_cmd_status

class Command:
  def __init__(self, name, spec):
    self.name = name
    self.timeout = spec.get("timeout", 0)
    self.status = spec.get("status")
    if not self.status:
      self.status = get_cmd_status(name)


class Config:
  _data: ConfigObj
  _file_name = None

  def __init__(self, src):
    if isinstance(src, dict):
      self._data = src
    else:
      self._file_name = src
      self._data = ConfigObj(src)

  def get_cmd(self, cmd) -> Command:
    spec = self._data.get("commands", {}).get(cmd)
    if not spec:
      raise Exception(f"Command not found: {cmd}")
    return Command(cmd, spec)

  def value(self, path):
    val = self._data
    for key in path.split("/"):
      if key not in val:
        raise KeyError(f"Configuration path not found: {path}")
      val = val[key]
    # Without config spec all values are strings by default
    # Try to convert string values to appropriate types
    if isinstance(val, str):
      if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
        return int(val)
      try:
        return float(val)
      except ValueError:
        pass
    return val

  def set_value(self, path, value):
    keys = path.split("/")
    val = self._data
    for key in keys[:-1]:
      if key not in val:
        raise KeyError(f"Configuration path not found: {path}")
      val = val[key]
    val[keys[-1]] = value

  def save(self):
    if not self._file_name:
      raise Exception("Cannot save: no config file specified")
    self._data.write()
