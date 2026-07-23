import json
import os
import pathlib
import sys
import numpy as np
from PySide6.QtGui import QIcon
from PySide6.QtCore import QObject, QEvent, QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox, QWidget

_APP_DIR: str = ''

# To use as a parent for dialogs
_DIALOG_PARENT: QWidget|None = None

from consts import APP_NAME

def set_dialog_parent(w: QWidget):
  global _DIALOG_PARENT
  _DIALOG_PARENT = w

def app_dir(file_name = None) -> str:
  global _APP_DIR
  if not _APP_DIR:
    if getattr(sys, 'frozen', False):
      # Running in a PyInstaller bundle
      _APP_DIR = getattr(sys, '_MEIPASS')
    else:
      # Running in dev Python environment
      _APP_DIR = str(pathlib.Path(__file__).resolve().parent)
  if file_name:
    return os.path.join(_APP_DIR, file_name)
  return _APP_DIR

def load_icon_svg(icon_file) -> QIcon:
  fn = icon_file
  if not fn.endswith(".svg") and not fn.endswith(".png"):
    fn += ".svg"
  fn = os.path.join(app_dir(), "img", fn)
  #print("Load icon", fn)
  return QIcon(fn)

def load_icon_png(icon_file) -> QIcon:
  fn = icon_file
  if not fn.endswith(".png"):
    fn += ".png"
  fn = os.path.join(app_dir(), "img", fn)
  #print("Load icon", fn)
  return QIcon(fn)

_ICONS = {}

def load_icon_zip(icon_file) -> QIcon:
  fn = icon_file
  if fn.endswith(".png"):
    return load_icon_png(fn)
  if not fn.endswith(".svg"):
    fn += ".svg"
  if len(_ICONS) == 0:
    from zipfile import ZipFile
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap, QPainter
    from PySide6.QtSvg import QSvgRenderer
    icons_zip = os.path.join(app_dir(), 'img', 'icons.zip')
    with ZipFile(icons_zip, mode='r') as z:
      for name in z.namelist():
        #print(f"Load icon", os.path.join(icons_zip, name))
        svg_bytes = z.read(name)
        renderer = QSvgRenderer(svg_bytes)
        pixmap = QPixmap(200, 200)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        _ICONS[name] = QIcon(pixmap)
  return _ICONS[fn] if fn in _ICONS else QIcon()

#load_icon = load_icon_svg
#load_icon = load_icon_png
load_icon = load_icon_zip

def load_json(file_name) -> dict:
  fn = app_dir(file_name)
  if not os.path.exists(fn):
    raise Exception(f"File not found: {fn}")
  with open(fn, 'r') as f:
    try:
      return json.load(f)
    except Exception as e:
      raise Exception(f"Failed to parse file {fn}: {e}")

def make_sample_profile(start_pos = 10.0, scan_range = 20.0):
  profile_center = start_pos + scan_range / 2.0
  y_max = 1000
  profile_width = scan_range / 10.0
  num_points = 101
  noise_level = 0.05
  x = np.linspace(start_pos, start_pos + scan_range, num_points)
  profile = y_max * np.exp(-((profile_center-x)**2) / (2 * profile_width**2))
  noise = np.random.normal(0, y_max * noise_level, num_points)
  background = 0.2 * y_max
  y = profile + noise + background
  return (x, y)

def calc_background_level(signal: np.ndarray, point_percent = 5):
  """
  Calculates background level of the given profile values.
  The background level is average of several first and last data points;
  a number of points for averaging is  given as percent of total point count.
  """
  n = max(1, int(len(signal) * point_percent / 100))
  return np.mean(np.concatenate([signal[:n], signal[-n:]]))

class VisibilityEventFilter(QObject):
  """
  Event filter to track visibility of a widget and change visibility of another one
  """
  def __init__(self, target, parent=None):
    super().__init__(parent)
    self.target = target

  def eventFilter(self, obj, event):
    if event.type() == QEvent.Type.Show:
      self.target.show()
    elif event.type() == QEvent.Type.Hide:
      self.target.hide()
    return super().eventFilter(obj, event)

def app_settings() -> QSettings:
  s = QSettings(QSettings.Format.IniFormat, QSettings.Scope.UserScope, "orion-project.org", "pulse-inspector")
  return s

def input_float_dlg(prompt: str, value: float) -> float|None:
  text, ok = QInputDialog.getText(_DIALOG_PARENT, APP_NAME, prompt, text=str(value))
  if not ok:
    return None
  try:
    return float(text)
  except ValueError:
    QMessageBox.critical(_DIALOG_PARENT, APP_NAME, "Invalid numeric value")
    return None
