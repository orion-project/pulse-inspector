import json
import os
import pathlib

from PySide6.QtGui import QIcon

_APP_DIR: str = None

def app_dir(file_name = None) -> str:
  global _APP_DIR
  if not _APP_DIR:
    _APP_DIR = pathlib.Path(__file__).resolve().parent
  if file_name:
    return os.path.join(_APP_DIR, file_name)
  return _APP_DIR

def load_icon(icon_file) -> QIcon:
  return QIcon(os.path.join(app_dir(), 'img', icon_file))

def load_json(file_name) -> dict:
  fn = app_dir(file_name)
  if not os.path.exists(fn):
    raise Exception(f"File not found: {fn}")
  with open(fn, 'r') as f:
    try:
      return json.load(f)
    except Exception as e:
      raise Exception(f"Failed to parse file {fn}: {e}")
