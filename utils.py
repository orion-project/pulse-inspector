import os
import pathlib

from PySide6.QtGui import QIcon

_APP_DIR = None

def app_dir():
    global _APP_DIR
    if not _APP_DIR:
        _APP_DIR = pathlib.Path(__file__).resolve().parent
    return _APP_DIR

def load_icon(icon_file):
    return QIcon(os.path.join(app_dir(), 'img', icon_file))
