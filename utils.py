import json
import os
import pathlib
import sys

from PySide6.QtGui import QIcon

_APP_DIR: str = None

def app_dir(file_name = None) -> str:
  global _APP_DIR
  if not _APP_DIR:
    if getattr(sys, 'frozen', False):
      # Running in a PyInstaller bundle
      _APP_DIR = sys._MEIPASS
    else:
      # Running in dev Python environment
      _APP_DIR = pathlib.Path(__file__).resolve().parent
  if file_name:
    return os.path.join(_APP_DIR, file_name)
  return _APP_DIR

def load_icon(icon_file) -> QIcon:
  fn = icon_file
  if not fn.endswith(".svg") and not fn.endswith(".png"):
    fn += ".svg"
  return QIcon(os.path.join(app_dir(), 'img', fn))

def load_json(file_name) -> dict:
  fn = app_dir(file_name)
  if not os.path.exists(fn):
    raise Exception(f"File not found: {fn}")
  with open(fn, 'r') as f:
    try:
      return json.load(f)
    except Exception as e:
      raise Exception(f"Failed to parse file {fn}: {e}")
