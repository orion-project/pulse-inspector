from configobj import ConfigObj

def _is_int(v: str) -> bool:
  return v.isdigit() or (v.startswith('-') and v[1:].isdigit())

def _convert(val):
  # Without config spec all values are strings by default
  # Try to convert string values to appropriate types
  if isinstance(val, str):
    v = val.lower()
    if v == "false":
      return False
    if v == "true":
      return True
    if _is_int(v):
      return int(v)
    try:
      return float(v)
    except ValueError:
      pass
  return val


class Command:
  name: str
  serial_name: str
  timeout: float
  log_answer: bool

  def __init__(self, name, specs):
    spec = specs.get(name)
    if not spec:
      raise KeyError(f"Command not found: {name}")

    self.name = name
    self.serial_name = spec.get("serial_name")
    self.log_answer = _convert(spec.get("log_answer", True))

    timeout = spec.get("timeout")
    if not timeout:
      timeout = specs.get("timeout", 1)
    self.timeout = _convert(timeout)

def _parse_range(s: str) -> list:
  r = [r.strip() for r in s.split("-")]
  if len(r) != 2:
    return None
  if _is_int(r[0]) and _is_int(r[1]):
    min = int(r[0])
    max = int(r[1])
  else:
    try:
      min = float(r[0])
    except ValueError:
      print(f"Invalid range: {s}")
      return None
    try:
      max = float(r[1])
    except ValueError:
      print(f"Invalid range: {s}")
      return None
  if max < min:
    min, max = max, min
  return (min, max)

class Parameter:
  name: str
  title: str
  options: list = []
  range: tuple = None
  precision = 2
  step = None

  def __init__(self, name, specs):
    spec = specs.get(name)
    if not spec:
      raise KeyError(f"Parameter not found: {name}")

    self.name = name

    self.title = spec.get("title")
    if not self.title:
      self.title = name

    opts = spec.get("options")
    if opts and isinstance(opts, list):
      self.options = opts

    self.range = _parse_range(spec.get("range", ""))

    precision = spec.get("precision")
    if precision is not None:
      self.precision = _convert(precision)

    step = spec.get("step")
    if step:
      self.step = _convert(step)

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

  def param_spec(self, code: str) -> Parameter:
    specs = self._data.get("parameters")
    if not specs:
      raise KeyError(f"Parameter not found: {code}")
    return Parameter(code, specs)

  def param_codes(self):
    specs = self._data.get("parameters")
    if not specs:
      raise KeyError(f"Parameters not found")
    return [*specs]

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
