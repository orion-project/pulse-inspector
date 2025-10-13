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
