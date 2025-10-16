import logging
import threading
from PySide6.QtCore import QObject, Signal

from config import Config
from consts import CMD

board = None

class Board(QObject):
  on_command_beg = Signal(CMD)
  on_command_end = Signal(CMD, str)

  _cmd: CMD = None
  _next_cmd: CMD = None
  _cancel_cmd = False
  _cmd_start = 0
  _cmd_timeout = 0
  _cmd_args: dict = None

  connected = False
  homed = False

  can_connect = True
  can_home = False
  can_move = False
  can_jog = False
  can_stop = False

  position: float = None

  log: logging.Logger

  def __init__(self, log, config_file):
    super().__init__()

    self.log = log
    self.config = Config(config_file)

    self._lock = threading.Lock()
    self._thread = threading.Thread(target=self.loop, daemon=True)
    self._thread.start()

    global board
    board = self

  def _disable_all(self):
    self.can_connect = False
    self.can_home = False
    self.can_move = False
    self.can_jog = False
    self.can_stop = False

  def toggle_connection(self):
    self._lock.acquire()
    try:
      if not self.can_connect:
        self.log.debug("connect:disabled")
        return
      self._disable_all()
      if self.connected:
        self._next_cmd = CMD.disconnect
        self._cancel_cmd = True
      else:
        self._next_cmd = CMD.connect
    finally:
      self._lock.release()

  def _connect_done(self, ok):
    self._disable_all()
    self.connected = ok
    self.homed = False
    self.position = None
    self.can_connect = True
    self.can_home = ok
    self.can_jog = ok

  def _disconnect_done(self):
    self._disable_all()
    self.connected = False
    self.homed = False
    self.position = None
    self.can_connect = True

  def home(self):
    self._lock.acquire()
    try:
      if not self.can_home:
        self.log.debug("home:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.home
      self.homed = False
      self.position = None
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def _home_done(self, ok):
    self._disable_all()
    self.homed = ok
    # self.position is assigned by the board command handler
    # it not necessary must be 0
    self.can_connect = True
    self.can_home = True
    self.can_move = ok
    self.can_jog = True

  def stop(self):
    self._lock.acquire()
    try:
      if not self.can_stop:
        self.log.debug("stop:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.stop
      self._cancel_cmd = True
      self.can_connect = True
    finally:
      self._lock.release()

  def _stop_done(self):
    self._disable_all()
    self.can_connect = True
    self.can_home = True
    self.can_move = self.homed
    self.can_jog = True

  def move(self, pos: float):
    self._lock.acquire()
    try:
      if not self.can_move:
        self.log.debug("move:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.move
      self._cmd_args = {"pos": pos}
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def _move_done(self, ok):
    self._disable_all()
    if not ok:
      # Position lost
      self.homed = False
      self.position = None
    else:
      # self.position is assigned by the board command handler
      pass
    self.can_connect = True
    self.can_home = True
    self.can_move = ok
    self.can_jog = True

  def _end_command(self, err):
    ok = not err
    if ok:
      self.log.info(f"end:{self._cmd}")
    self._lock.acquire()
    try:
      if self._cmd == CMD.connect:
        self._connect_done(ok)
      elif self._cmd == CMD.disconnect:
        self._disconnect_done()
      elif self._cmd == CMD.home:
        self._home_done(ok)
      elif self._cmd == CMD.stop:
        self._stop_done()
      elif self._cmd == CMD.move:
        self._move_done(ok)
    finally:
      self._lock.release()
    self.on_command_end.emit(self._cmd, err)
    self._cmd = None
    self._cmd_start = 0
    self._cmd_timeout = 0
    self._cmd_args = None
