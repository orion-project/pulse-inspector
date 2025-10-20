import logging
import threading
from PySide6.QtCore import QObject, Signal

from config import Config
from consts import CMD

board = None

class Board(QObject):
  on_command_beg = Signal(CMD)
  on_command_end = Signal(CMD, str)
  on_data_received = Signal(list, list)
  on_params_received = Signal()
  on_param_stored = Signal(bool)
  on_stage_moved = Signal()

  _cmd: CMD = None
  _next_cmd: CMD = None
  _cancel_cmd = False
  _cmd_start = 0
  _cmd_timeout = 0
  _cmd_args: dict = {}

  connected = False
  homed = False
  params: dict = {}

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
        self.log.warning("connect:disabled")
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
        self.log.warning("home:disabled")
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
        self.log.warning("stop:disabled")
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
        self.log.warning("move:disabled")
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

  def _jog(self, offset: float):
    self._lock.acquire()
    try:
      if not self.can_jog:
        self.log.warning("jog:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.jog
      self._cmd_args = {"offset": offset}
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def jog_forth(self):
    self._jog(self.config.value("operations/jog_distance", 0.25))

  def jog_forth_long(self):
    self._jog(self.config.value("operations/jog_distance_long", 1))

  def jog_back(self):
    self._jog(-self.config.value("operations/jog_distance", 0.25))

  def jog_back_long(self):
    self._jog(-self.config.value("operations/jog_distance_long", 1))

  def scan(self):
    self._lock.acquire()
    try:
      if not self.can_move:
        self.log.warning("scan:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.scan
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def scans(self):
    self._lock.acquire()
    try:
      if not self.can_move:
        self.log.warning("scans:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.scans
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

  def query_params(self):
    self._lock.acquire()
    try:
      if not self.can_home:
        self.log.warning("read_params:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.param
      self.can_connect = True
      self.can_stop = True
      self._cmd_args = {}
    finally:
      self._lock.release()

  def _query_params_done(self):
    self._disable_all()
    self.can_connect = True
    self.can_home = True
    self.can_move = self.homed
    self.can_jog = True

  def store_params(self, params: dict):
    self.log.info(f"changes:{params}({len(params)})")
    self._cmd_args = {"store": True, "params": params}
    self.store_next_param()

  def store_next_param(self):
    print("store next param")
    self._lock.acquire()
    try:
      if not self.can_home:
        self.log.warning("store_param:disabled")
        return
      self._disable_all()
      self._next_cmd = CMD.param
      self.can_connect = True
      self.can_stop = True
    finally:
      self._lock.release()

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
      elif self._cmd == CMD.move or self._cmd == CMD.jog \
        or self._cmd == CMD.scan or self._cmd == CMD.scans:
        self._move_done(ok)
      elif self._cmd == CMD.param:
        self._query_params_done()
    finally:
      self._lock.release()
    self.on_command_end.emit(self._cmd, err)
    self._cmd = None
    self._cmd_start = 0
    self._cmd_timeout = 0
    # Don't clear args at any command end
    # There can be sequential commands using the same args (e.g. params storing)
    # Args should be initialized before a command whch is going to use them
    # Remaining commands do not care about args
    #self._cmd_args = {}

  def get_cmd_run_text(self, cmd: CMD) -> str:
    if cmd == CMD.connect:
      return "Connecting..."
    if cmd == CMD.disconnect:
      return "Disconnecting..."
    if cmd == CMD.home:
      return "Homing..."
    if cmd == CMD.stop:
      return "Stopping..."
    if cmd == CMD.move or cmd == CMD.jog:
      return "Moving..."
    if cmd == CMD.scan or cmd == CMD.scans:
      return "Scanning..."
    if cmd == CMD.param:
      if self._cmd_args.get("store"):
        return "Storing parameters..."
      return "Reading parameters..."
    return cmd.value.title() + "..."
