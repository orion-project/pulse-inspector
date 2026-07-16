import re
from configobj import ConfigObj
from typing import overload, Any, Callable, Type

class ConfigSection:
  _data: dict[str, Any]

  def __init__(self, data: dict[str, Any]):
    self._data = data

  @overload
  def get(self, type: Type[str], key: str, default: str|None) -> str: ...

  @overload
  def get(self, type: Type[bool], key: str, default: bool|None) -> bool: ...

  @overload
  def get(self, type: Type[int], key: str, default: int|None) -> int: ...

  @overload
  def get(self, type: Type[float], key: str, default: float|None) -> float: ...

  @overload
  def get(self, type: Type[list], key: str, default: list|None) -> list: ...

  def get(self, type: Callable[[str], Any], key: str, default: Any) -> Any:
    # Without config spec all values are strings by default
    # Try to convert string values to appropriate types
    val = self._data.get(key)
    if val is None:
      if default is None:
        raise KeyError(f"Value '{key}' not found in config")
      return default

    if type is bool:
      v = val.lower()
      if v == "false":
        return False
      if v == "true":
        return True
      raise ValueError(f"Value '{key}' is not a boolean")

    if type is list:
      if isinstance(val, list):
        return val
      raise ValueError(f"Value '{key}' is not a list")

    return type(val)

  def has(self, key: str) -> bool:
    return key in self._data

class Command:
  name: str
  serial_name: str
  timeout: float
  log_answer: bool

  def __init__(self, name, specs: dict[str, Any]):
    spec = specs.get(name)
    if not spec:
      raise KeyError(f"Command not found: {name}")

    spec = ConfigSection(spec)

    self.name = name
    self.serial_name = spec.get(str, "serial_name", name)
    self.log_answer = spec.get(bool, "log_answer", True)

    if spec.has("timeout"):
      self.timeout = spec.get(float, "timeout", None)
    else:
      # If the command doesn't provide its own timeout
      # use the global default timeout given for all commands
      spec = ConfigSection(specs)
      self.timeout = spec.get(float, "timeout", 1)

class ValueRange:
  min: float|int
  max: float|int
  step: float|int

  def __init__(self, min: float|int, max: float|int):
    self.min = min
    self.max = max
    self.step = 0

def _parse_range(s: str) -> ValueRange|None:
  r = [r.strip() for r in s.split("-")]
  if len(r) != 2:
    return None
  try:
    min = int(r[0])
    max = int(r[1])
  except ValueError:
    try:
      min = float(r[0])
      max = float(r[1])
    except ValueError:
      print(f"Invalid range: {s}")
      return None
  if max < min:
    min, max = max, min
  return ValueRange(min, max)

class Parameter:
  name: str
  title: str
  options: list = []
  range: ValueRange|None = None
  precision = 2

  def __init__(self, name, specs: dict[str, Any]):
    spec = specs.get(name)
    if not spec:
      raise KeyError(f"Parameter not found: {name}")

    spec = ConfigSection(spec)

    self.name = name
    self.title = spec.get(str, "title", name)
    self.options = spec.get(list, "options", [])
    self.precision = spec.get(int, "precision", 2)
    self.range = _parse_range(spec.get(str, "range", ""))
    if self.range:
      self.range.step = spec.get(float, "step", 0)

class ScanRange:
  name: str
  range: float

  def __init__(self, text: str):
    match = re.match(r'^(.+?)\s*\((.+?)\)$', text)
    if match:
      self.range = float(match.group(1).strip())
      self.name = match.group(2).strip()
    else:
      raise ValueError(f"Invalid format for ScanRange: {text}. Expected 'value (name)'")

class Config:
  _data: ConfigObj
  _file_name: str = ''
  _cache: dict[str, Any] = {}

  def __init__(self, src: dict|str):
    if isinstance(src, dict):
      self._data = ConfigObj(src)
    else:
      self._file_name = src
      self._data = ConfigObj(src)

  def cmd_spec(self, name: str) -> Command:
    key = f"CMD:{name}"
    if name in self._cache:
      return self._cache[key]
    specs = self._data.get("commands")
    if not isinstance(specs, dict):
      raise ValueError("The [commands] section not found config or has bad format")
    cmd = Command(name, specs)
    self._cache[key] = cmd
    return cmd

  def param_spec(self, name: str) -> Parameter:
    key = f"PARAM:{name}"
    if key in self._cache:
      return self._cache[key]
    specs = self._data.get("parameters")
    if not isinstance(specs, dict):
      raise ValueError("The [parameters] section not found config or has bad format")
    param = Parameter(name, specs)
    self._cache[key] = param
    return param

  def param_codes(self):
    specs = self._data.get("parameters")
    if not specs:
      raise KeyError(f"Parameters not found")
    return [*specs]

  @overload
  def value(self, type: Type[str], path: str, default: str|None) -> str: ...

  @overload
  def value(self, type: Type[bool], path: str, default: bool|None) -> bool: ...

  @overload
  def value(self, type: Type[int], path: str, default: int|None) -> int: ...

  @overload
  def value(self, type: Type[float], path: str, default: float|None) -> float: ...

  @overload
  def value(self, type: Type[list], path: str, default: list|None) -> list: ...

  def value(self, type: Callable[[str], Any], path: str, default = None) -> Any:
    if path in self._cache:
      return self._cache[path]
    val = self._data
    for key in path.split("/"):
      if key not in val:
        if default is not None:
          return default
        raise KeyError(f"Configuration path not found: {path}")
      val = val[key]
    # Convert to desired type
    tmp = ConfigSection({'tmp': val})
    val = tmp.get(type, 'tmp', None)
    self._cache[path] = val
    return val

  def set_value(self, path: str, value):
    keys = path.split("/")
    val: Any = self._data
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

  def error_text(self, err) -> str:
    msg = ''
    code = err.split(" ")[-1]
    errors = self._data.get("errors", {})
    if isinstance(errors, dict):
      msg = errors.get(code)
    if not msg:
      msg = f"error={code}"
    return msg

  def scan_ranges(self) -> list[ScanRange]:
    key = "operations/scan_ranges"
    # Several ranges
    items = self.value(list, key, [])
    if len(items) > 0:
      res = []
      for item in items:
        if not isinstance(item, str):
          raise TypeError(f"{key} has bad type, string or string-list expected")
        res.append(ScanRange(item))
      return res
    # Single range
    item = self.value(str, key, "")
    if item:
      return [ScanRange(item)]
    raise TypeError(f"{key} has bad type, string or string-list expected")
