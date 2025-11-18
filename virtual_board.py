import logging
import time

from board import Board
from consts import CMD
from utils import make_sample_profile

log = logging.getLogger(__name__)

def ms(v): return v/1000.0

MOVE_SPEED = 100 # mkm/s
MOVE_DELTA = ms(10)
JOG_SPEED = 100 # mkm/s
JOG_DELTA = ms(100)
SCAN_RANGE = 20
POS_EPSILON = 0.1 # mkm

class VirtualBoard(Board):
  # Current position of the stage as it's known by the firmware
  # Unlike self.position wich is what is known by the software
  _stage_position = 0 #

  _cmd_error = None
  _params_received = 0
  _stored_params = {
    "p1": "Hello World",
    "p2": "42",
    "p3": "7.0001",
    "p4": "1",
    "p5": "32"
  }

  def __init__(self):
    super().__init__(log, \
      {
        "commands": {
          CMD.connect: { "timeout": 0.5 },
          CMD.disconnect: { "timeout": 0.5 },
          CMD.home: { "timeout": 2 },
          CMD.stop: { "timeout": 0.5 },
          CMD.move: { "timeout": -1 }, # use MOVE_SPEED
          CMD.jog: { "timeout": -1 }, # use JOG_SPEED
          CMD.scan: { "timeout": 0.05 }, # between points
          CMD.scans: { "timeout": 0.25 },
          CMD.param: { "timeout": 0.10 },
        },
        "operations": {
          "jog_distance": 100,
          "jog_distance_long": 500,
          "scan_ranges": ["20 (Short)", "40 (Medium)", "100 (Long)"]
        },
        "parameters": {
          "p1": {
            "title": "Simple parameter with very long title " +
              "(can hold any value, it is up to the formware how to parse it)"
          },
          "p2": {
            "title": "Integer parameter",
            "range": "10 - 100",
            "step": 10
          },
          "p3": {
            "title": "Float value",
            "range": "0 - 10.5",
            "precision": 4,
            "step": 0.5,
          },
          "p4": {
            "title": "Two options 0 and 1 are renderd as flag",
            "options": ["0", "1"],
          },
          "p5": {
            "title": "Selector",
            "options": ["8", "16", "32", "64"],
          }
        }
      }
    )

  def port(self):
    return "VIRTUAL"

  def loop(self):
    while True:
      time.sleep(0.001)

      self._lock.acquire()
      next_cmd = self._next_cmd
      cancel = self._cancel_cmd
      self._lock.release()

      try:
        # A command in progress
        if self._cmd_start > 0:
          # There are some commands that can cancel
          # other commands without finishing them
          if cancel:
            log.info(f"cancel:{self._cmd}")
          else:
            elapsed = time.perf_counter() - self._cmd_start
            # Commands having timeout simulate their processing just by waiting for timeout
            if self._cmd_timeout > 0:
              if elapsed >= self._cmd_timeout:
                if self._command_done():
                  self._end_command(None)
            else:
              if self._process_command(elapsed):
                if self._command_done():
                  self._end_command(None)
            continue

        if self._cmd_error:
          err = self._cmd_error
          self._cmd_error = None
          raise Exception(err)

        if next_cmd:
          self._lock.acquire()
          self._next_cmd = None
          self._cancel_cmd = False
          self._lock.release()

          self._cmd = next_cmd
          log.info(f"begin:{self._cmd}")
          cmd = self.config.cmd_spec(self._cmd)
          self._prepare_command()
          self.on_command_beg.emit(self._cmd)
          self._cmd_start = time.perf_counter()
          self._cmd_timeout = cmd.timeout

      except Exception as e:
        log.exception(f"error:{self._cmd}")
        self._end_command(str(e))

  def _position_recieved(self):
    # Here we simulate that a position has been read from the firmware
    # Arduino rounds float values when sending them via Serial.print
    # so we round here as well
    self.position = round(self._stage_position, 2)

  def _position_str(self):
    return f"pos={self.position}, stage_pos={self._stage_position:.2f}"

  def _prepare_command(self):
    # Do some stuff before command start
    if self._cmd == CMD.param:
      self._params_received = 0
    elif self._cmd == CMD.move:
      self._mov_start = self._stage_position
      self._mov_target = self._cmd_args.get("pos", 0)
      self._mov_prev_time = 0
      self._mov_delta = MOVE_DELTA
      offset = self._mov_target - self._stage_position
      self._mov_speed = MOVE_SPEED * (1 if offset > 0 else -1)
      print(f"mov: {self._position_str()}, target={self._mov_target}, speed={self._mov_speed}")
    elif self._cmd == CMD.jog:
      offset = self._cmd_args.get("offset", 0)
      self._mov_start = self._stage_position
      self._mov_target = self._mov_start + offset
      self._mov_prev_time = 0
      self._mov_delta = JOG_DELTA
      self._mov_speed = JOG_SPEED * (1 if offset > 0 else -1)
      print(f"mov: {self._position_str()}, target={self._mov_target}, speed={self._mov_speed}")
    elif self._cmd == CMD.scan:
      self._scan_points_x = []
      self._scan_points_y = []
      self._scan_point_index = 0
      self._scan_center = self._stage_position
      # move the stage to the start scan position
      # so the single scan loop looks like
      #
      # |<---- move to start ----- x
      # |---->---- scan ---->---- scan ---->---- scan ---->----|
      #                            x <--- restore position ----|
      #
      # Here we don't have _position_recieved() because the software does not know
      # that firmware decides to moves the stage in order to prepare for scanninig
      scan_range = SCAN_RANGE if self._scan_range is None else self._scan_range
      self._stage_position -= scan_range/2
      (x, y) = make_sample_profile(self._stage_position, scan_range)
      self._scan_profile_x = x  # precalculate profile data
      self._scan_profile_y = y  # will be used for scan steps
      print(f"scan: {self._position_str()}, points={len(self._scan_profile_x)}, range={scan_range}")

  def _process_command(self, elapsed: float) -> bool:
    if self._cmd == CMD.jog or self._cmd == CMD.move:
      # Skip moving if we already at target
      if abs(self._mov_target - self._mov_start) < POS_EPSILON:
        return True
      # Do moving by small steps
      delta = elapsed - self._mov_prev_time
      if delta < self._mov_delta:
        return False
      step = self._mov_speed * delta
      self._stage_position += step
      self._mov_prev_time = elapsed
      print(f"mov: delta={delta*1000:.2f}, step={step:.2f}, {self._position_str()}")
      if (abs(self._mov_target - self._stage_position) < POS_EPSILON) \
        or (self._mov_speed > 0 and self._stage_position > self._mov_target) \
        or (self._mov_speed < 0 and self._stage_position < self._mov_target):
          return True
    return False

  def _command_done(self) -> bool:
    if self._cmd == CMD.home:
      self._stage_position = 0
      self._position_recieved()
      return True

    if self._cmd == CMD.move:
      self._position_recieved()
      print(f"mov: {self._position_str()}")
      return True

    if self._cmd == CMD.jog:
      if self.position is not None:
        self._position_recieved()
      print(f"mov: {self._position_str()}")
      return True

    if self._cmd == CMD.scan:
      x = self._scan_profile_x[self._scan_point_index]
      y = self._scan_profile_y[self._scan_point_index]
      self._stage_position = x
      print(f"scan: point={self._scan_point_index}, {self._position_str()}, level={y:.2f}")
      self._scan_points_x.append(x)
      self._scan_points_y.append(y)
      self._position_recieved()
      self.on_stage_moved.emit()
      self._scan_point_index += 1
      if self._scan_point_index == len(self._scan_profile_x):
        # Restore the initial position.
        self._stage_position = self._scan_center
        self._position_recieved()
        self.on_data_received.emit(self._scan_points_x, self._scan_points_y)
        print(f"scan: {self._position_str()}")
        return True
      # Continue to the next scan point
      self._cmd_start = time.perf_counter()
      return False

    if self._cmd == CMD.scans:
      self.on_data_received.emit(*make_sample_profile())
      self._cmd_start = time.perf_counter()
      return False

    if self._cmd == CMD.param:
      if self._cmd_args.get("store"):
        # Store params
        params = self._cmd_args["params"]
        name = [*params][0]
        value = params[name]
        self._stored_params[name] = value
        log.info(f"param_stored:{name}={value}")
        del params[name]
        self.on_param_stored.emit(len(params) > 0)
        return True
      else:
        # Receive params
        names = [*self._stored_params]
        name = names[self._params_received]
        self.params[name] = self._stored_params[name]
        self._params_received += 1
        log.debug(f"param_received:{self._params_received}/{len(names)}:{name}={self.params[name]}")
        if self._params_received == len(names):
          self.on_params_received.emit()
          return True
        self._cmd_start = time.perf_counter()
        return False

    return True

  def debug_simulate_disconnection(self):
    if not self.connected:
      return
    self._cmd = CMD.disconnect
    self._cmd_error = "Connection interrupted"
    self._cancel_cmd = True

  def debug_simulate_command_error(self):
    if not self.connected:
      return
    self._cmd_error = "Something did not go"
    self._cancel_cmd = True
