import json
import os
import pathlib
import sys
import numpy as np
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

def make_sample_profile():
  start_pos = 10
  scan_range = 20
  profile_center = start_pos + scan_range / 2.0
  y_max = 1000
  profile_width = scan_range / 10.0
  num_points = 201
  noise_level = 0.05
  x = np.linspace(start_pos, start_pos + scan_range, num_points)
  profile = y_max * np.exp(-((profile_center-x)**2) / (2 * profile_width**2))
  noise = np.random.normal(0, y_max * noise_level, num_points)
  y = profile + noise
  return (x, y)
