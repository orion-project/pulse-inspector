from configobj import ConfigObj

def _convert(val):
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


class Command:
  name: str
  serial_name: str
  timeout: float

  def __init__(self, name, specs):
    spec = specs.get(name)
    if not spec:
      raise KeyError(f"Command not found: {name}")

    self.name = name
    self.serial_name = spec.get("serial_name")

    timeout = spec.get("timeout")
    if not timeout:
      timeout = specs.get("timeout", 1)
    self.timeout = _convert(timeout)


class Config:
  _data: ConfigObj
  _file_name = None
  _cache = {}

  def __init__(self, src):
    if isinstance(src, dict):
      self._data = src
    else:
      self._file_name = src
      self._data = ConfigObj(src)

  def cmd_spec(self, name: str) -> Command:
    if name in self._cache:
      return self._cache[name]
    specs = self._data.get("commands")
    if not specs:
      raise KeyError(f"Command not found: {name}")
    cmd = Command(name, specs)
    self._cache[name] = cmd
    return cmd

  def value(self, path: str, default = None):
    if path in self._cache:
      return self._cache[path]
    val = self._data
    for key in path.split("/"):
      if key not in val:
        if default is not None:
          return default
        raise KeyError(f"Configuration path not found: {path}")
      val = val[key]
    val = _convert(val)
    self._cache[path] = val
    return val

  def set_value(self, path: str, value):
    keys = path.split("/")
    val = self._data
    for key in keys[:-1]:
      if key not in val:
        raise KeyError(f"Configuration path not found: {path}")
      val = val[key]
    val[keys[-1]] = value
    self._cache[path] = value

  def save(self):
    if not self._file_name:
      raise Exception("File name is not specified")
    self._data.write()

  def error_text(self, err):
    code = err.split(" ")[-1]
    msg = self._data.get("errors", {}).get(code)
    if not msg:
      msg = f"error={code}"
    return msg
