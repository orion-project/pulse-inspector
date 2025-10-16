import threading
from PySide6.QtCore import QObject, Signal

from config import Config
from consts import CMD_CONNECT, CMD_DISCONNECT, CMD_HOME, CMD_STOP

class Board(QObject):
  on_command_beg = Signal(str)
  on_command_end = Signal(str, str)

  _cmd = None
  _next_cmd = None
  _cancel_cmd = False
  _cmd_start = 0
  _cmd_timeout = 0

  connected = False
  homed = False

  can_connect = True
  can_home = False
  can_move_abs = False
  can_move_rel = False
  can_stop = False

  def __init__(self, config_file: str):
    super().__init__()

    self.config = Config(config_file)

    self._lock = threading.Lock()
    self._thread = threading.Thread(target=self.loop, daemon=True)
    self._thread.start()

  def _disable_all(self):
    self.can_connect = False
    self.can_home = False
    self.can_move_abs = False
    self.can_move_rel = False
    self.can_stop = False

  def toggle_connection(self):
    self._lock.acquire()
    try:
      if not self.can_connect:
        return
      if self.connected:
        self._next_cmd = CMD_DISCONNECT
        self._cancel_cmd = True
      else:
        self._next_cmd = CMD_CONNECT
      self._disable_all()
    finally:
      self._lock.release()

  def _connect_done(self, ok):
    self.connected = ok
    self.homed = False
    self._disable_all()
    self.can_connect = True
    self.can_home = ok
    self.can_move_rel = ok

  def _disconnect_done(self):
    self.connected = False
    self.homed = False
    self._disable_all()
    self.can_connect = True

  def home(self):
    self._lock.acquire()
    try:
      if not self.can_home:
        return
      self._next_cmd = CMD_HOME
      self.homed = False
      self._disable_all()
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def _home_done(self, ok):
    self.homed = ok
    self._disable_all()
    self.can_connect = True
    self.can_home = True
    self.can_move_abs = ok
    self.can_move_rel = True

  def stop(self):
    self._lock.acquire()
    try:
      if not self.can_stop:
        return
      self._next_cmd = CMD_STOP
      self._cancel_cmd = True
      self._disable_all()
      self.can_connect = True
    finally:
      self._lock.release()

  def _stop_done(self):
    self._disable_all()
    self.can_connect = True
    self.can_home = True
    self.can_move_abs = self.homed

  def _end_command(self, log, err):
    if not err:
      log.info(f"end:{self._cmd}")
    self._lock.acquire()
    try:
      if self._cmd == CMD_CONNECT:
        self._connect_done(not err)
      elif self._cmd == CMD_DISCONNECT:
        self._disconnect_done()
      elif self._cmd == CMD_HOME:
        self._home_done(not err)
      elif self._cmd == CMD_STOP:
        self._stop_done()
    finally:
      self._lock.release()
    self.on_command_end.emit(self._cmd, err)
    self._cmd = None
    self._cmd_start = 0
    self._cmd_timeout = 0

  def move(self):
    pass
