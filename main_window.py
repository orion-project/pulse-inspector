import logging
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QFontMetrics
from PySide6.QtWidgets import (
  QLabel, QMainWindow, QMessageBox, QStatusBar, QToolBar, QToolButton, QInputDialog)

from board import board
from board_params_dialog import BoardParamsDialog
from consts import APP_NAME, APP_VERSION, APP_PAGE, CMD
from plot import Plot, FIT
from utils import load_icon, app_settings, VisibilityEventFilter, make_sample_profile

log = logging.getLogger(__name__)

BUTTON_POS_MARGIN = 10
BUTTON_POS_MIN_W = 80

class MainWindow(QMainWindow):
  action_groups = {}
  action_handlers = {}
  checkable_actions = {}

  def __init__(self, dev_mode=False, scan_file=""):
    super().__init__()

    self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

    self.dev_mode = dev_mode

    self.plot = Plot(self)
    self.plot.main_window = self

    self.setCentralWidget(self.plot)

    self.create_menu_bar()
    self.create_tool_bar()
    self.create_status_bar()

    board.on_command_beg.connect(self.board_command_beg)
    board.on_command_end.connect(self.board_command_end)
    board.on_data_received.connect(self.plot.draw_graph)
    board.on_stage_moved.connect(self.show_position)
    board.on_idle.connect(self.show_level)

    self.load_settings()
    self.show_connection()
    self.update_actions()

    if scan_file:
      self.plot.open_graph(scan_file)
    elif self.dev_mode:
      self.plot.draw_graph(*make_sample_profile(), auto_save=False)

  def load_settings(self):
    # Load checked options
    s = app_settings()
    for name in self.action_groups:
      group = self.action_groups[name]
      checked_id = s.value(name)
      checked_found = False
      for a in group.actions():
        if a.objectName() == checked_id:
          checked_found = True
          a.setChecked(True)
          a.trigger()
          break
      if not checked_found:
        a = group.actions()[0]
        a.setChecked(True)
        a.trigger()
    # Load checked flags
    for action in self.checkable_actions:
      key = action.objectName()
      if key and s.contains(key):
        is_checked = s.value(key) == "true"
        action.setChecked(is_checked)
        self.checkable_actions[action](is_checked)
    # Load component settings
    self.plot.load_settings(s)

  def _action_handler(self):
    (handler, arg) = self.action_handlers[self.sender()]
    handler(arg)

  def _action_group_triggered(self, action):
    app_settings().setValue(self.sender().objectName(), action.objectName())

  def _checkable_action_triggered(self):
    sender = self.sender()
    if isinstance(sender, QAction):
      action: QAction = sender
      if action.objectName():
        app_settings().setValue(action.objectName(), action.isChecked())
      self.checkable_actions[action](action.isChecked())

  def create_menu_bar(self):

    def A(title, handler, menu, **kwargs):
      handler_added = False
      a = QAction(title, self)
      if "key" in kwargs:
        a.setShortcut(kwargs["key"])
      if "icon" in kwargs:
        a.setIcon(load_icon(kwargs["icon"]))
      if "hint" in kwargs:
        a.setToolTip(kwargs["hint"])
      if "group" in kwargs:
        [name, id] = kwargs["group"].split("|")
        group = self.action_groups.get(name)
        if not group:
          group = QActionGroup(self)
          group.setObjectName(name)
          group.setExclusive(True)
          group.triggered.connect(self._action_group_triggered)
          self.action_groups[name] = group
        a.setCheckable(True)
        a.setActionGroup(group)
        a.setObjectName(id)
      if "check" in kwargs:
        a.setCheckable(True)
        if "checked" in kwargs:
          a.setChecked(kwargs["checked"])
        # Pass id to make the check-state storable
        if "id" in kwargs:
          a.setObjectName(kwargs["id"])
        a.triggered.connect(self._checkable_action_triggered)
        self.checkable_actions[a] = handler
        handler_added = True
      if not handler_added:
        if "arg" in kwargs:
          self.action_handlers[a] = (handler, kwargs["arg"])
          a.triggered.connect(self._action_handler)
        else:
          a.triggered.connect(handler)
      if menu:
        menu.addAction(a)
      return a

    m = self.menuBar().addMenu("Board")
    self.act_connect = A("Connect", board.toggle_connection, m, icon="connect")
    self.act_disconnect = A("Disconnect", board.toggle_connection, m, icon="disconnect")
    self.act_board_params = A("Firmware Parameters...", board.query_params, m, icon="chip")
    m.addSeparator()
    A("Exit", self.close, m, key="Ctrl+Q")

    m = self.menuBar().addMenu("Move")
    self.act_home = A("Home", board.home, m, key="Ctrl+H", icon="home")
    m.addSeparator()
    self.act_jog_back_long = A("Jog Backward (long)", board.jog_back_long, m, key="Ctrl+Shift+Left", icon="jog_left_2")
    self.act_jog_back = A("Jog Backward", board.jog_back, m, key="Ctrl+Left", icon="jog_left")
    self.act_move = A("Go To Position...", self.go_to_position, m, key="Ctrl+G", icon="walk")
    self.act_get_position = A("Query Position", board.get_position, m, key="Ctrl+P", icon="position")
    self.act_jog_forth = A("Jog Forward", board.jog_forth, m, key="Ctrl+Right", icon="jog_right")
    self.act_jog_forth_long = A("Jog Forward (long)", board.jog_forth_long, m, key="Ctrl+Shift+Right", icon="jog_right_2")
    m.addSeparator()
    self.act_stop = A("Stop", board.stop, m, key="Ctrl+B", icon="stop")
    m.addSeparator()
    A("Use Microsteps For Jog", board.use_microstep_jog, m, check=True, id="microstep_jog")

    m = self.menuBar().addMenu("Scan")
    self.act_scan = A("Single", board.scan, m, key="F5", icon="scan_one", hint="Single Scan")
    self.act_scans = A("Continuous", board.scans, m, key="F9", icon="scan_cont", hint="Continuous Scanning")
    m.addSeparator()
    for r in board.config.scan_ranges():
      A(r.name, board.set_scan_range, m, group=f"scan_range|{r.range}", arg=r.range)
    m.addSeparator()
    self.act_save_data = A("Save Current Data...", self.plot.save_data_dlg, m, key="Ctrl+S", icon="save")
    A("Autosave Every Scan", self.plot.set_autosave, m, check=True, id="autosave")
    A("Choose Autosave Path...", self.plot.choose_autosave_dir, m)

    m = self.menuBar().addMenu("Fit")
    A("Gaussian", self.plot.set_fit, m, arg=FIT.gauss, group="fit_type|gauss")
    A("Lorentzian", self.plot.set_fit, m, arg=FIT.lorentz, group="fit_type|lorentz")
    A("sech²", self.plot.set_fit, m, arg=FIT.sech2, group="fit_type|sech")
    A("None", self.plot.set_fit, m, arg=FIT.none, group="fit_type|none")
    m.addSeparator()
    A("Fit Over Subrange", self.plot.set_fit_subrange, m, check=True, checked=False, id="fit_subrange")
    A("Set Fit Subrange...", self.plot.choose_fit_subrange, m)
    m.addSeparator()
    A("Adjust to Background", self.plot.set_shift_fit_bgnd, m, check=True, checked=True, id="shift_fit_bgnd")

    m = self.menuBar().addMenu("Plot")
    A("X - Show Delay", self.plot.show_x_delay, m, arg=True, group="plot_x|delay")
    A("X - Show Position", self.plot.show_x_delay, m, arg=False, group="plot_x|pos")
    m.addSeparator()
    A("Y - Show Raw Values", self.plot.show_y_norm, m, arg=False, group="plot_y|raw")
    A("Y - Show Normalized", self.plot.show_y_norm, m, arg=True, group="plot_y|norm")
    m.addSeparator()
    A("Zoom Both Axes", self.plot.set_zoom_mode, m, arg="xy", group="zoom_type|xy", icon="zoom")
    A("Zoom Only X-axis", self.plot.set_zoom_mode, m, arg="x", group="zoom_type|x", icon="zoom_x")
    A("Zoom Only Y-axis", self.plot.set_zoom_mode, m, arg="y", group="zoom_type|y", icon="zoom_y")
    A("Reset Zoom", self.plot.reset_zoom, m, key="Ctrl+0", icon="zoom_0")

    if self.dev_mode:
      m = self.menuBar().addMenu("Debug")
      A("Simulate disconnection", board.debug_simulate_disconnection, m)
      A("Simulate command error", board.debug_simulate_command_error, m)

    m = self.menuBar().addMenu('Help')
    A("Visit Project Page", self.show_homepage, m, icon="globe")
    m.addSeparator()
    A("About", self.show_about, m)
    A("About Qt", self.show_about_qt, m)

  def create_tool_bar(self):
    tb = QToolBar()
    tb.setIconSize(QSize(40, 40))
    tb.setMovable(False)
    tb.setFloatable(False)
    self.addToolBar(Qt.ToolBarArea.TopToolBarArea, tb)

    self.but_position_on = QToolButton()
    self.but_position_on.setToolTip("Current Position")
    self.but_position_on.setStyleSheet(f"QToolButton{{font-size: 20px; font-weight: bold; color: #00547f;}}")
    self.but_position_on.setFixedWidth(BUTTON_POS_MIN_W)
    self.but_position_on.clicked.connect(self.go_to_position)
    self.but_position_off = QToolButton()
    self.but_position_off.setToolTip("Current Position\n\nHoming required")
    self.but_position_off.setStyleSheet(f"QToolButton{{font-size: 20px; font-weight: bold; color: gray;}}")
    self.but_position_off.setFixedWidth(BUTTON_POS_MIN_W)
    self.but_position_off.setEnabled(False)

    tb.addAction(self.act_connect)
    tb.addAction(self.act_disconnect)
    tb.addAction(self.act_board_params)
    tb.addSeparator()
    tb.addAction(self.act_home)
    tb.addAction(self.act_jog_back_long)
    tb.addAction(self.act_jog_back)
    self.act_position_on = tb.addWidget(self.but_position_on)
    self.act_position_off = tb.addWidget(self.but_position_off)
    tb.addAction(self.act_jog_forth)
    tb.addAction(self.act_jog_forth_long)
    tb.addSeparator()
    tb.addAction(self.act_scan)
    tb.addAction(self.act_scans)
    tb.addSeparator()
    tb.addAction(self.act_stop)
    tb.addSeparator()
    tb.addAction(self.act_save_data)

  def create_status_bar(self):
    self.lab_connected = QLabel()
    self.lab_connected.setPixmap(load_icon("lamp_green").pixmap(16, 16))
    self.lab_connected.setContentsMargins(4, 0, 0, 0)
    self.lab_disconnected = QLabel()
    self.lab_disconnected.setPixmap(load_icon("lamp_gray").pixmap(16, 16))
    self.lab_disconnected.setContentsMargins(4, 0, 0, 0)

    self.lab_port = QLabel()
    self.lab_port.setContentsMargins(0, 0, 0, 2)

    self.lab_home_warn = QLabel()
    self.lab_home_warn.setPixmap(load_icon("home_warn").pixmap(16, 16))
    self.lab_home_warn.setToolTip("Homing required")

    self.lab_run = QLabel()
    self.lab_run.setContentsMargins(0, 0, 0, 2)
    self.lab_run.setVisible(False)

    def separator(buddy = None):
      lab = QLabel("⁞")
      lab.setStyleSheet("QLabel{color:silver;}")
      lab.setContentsMargins(4, 0, 4, 4)
      if buddy:
        buddy.installEventFilter(VisibilityEventFilter(lab, self))
        lab.setVisible(buddy.isVisible())
      return lab

    sb = QStatusBar()
    sb.addWidget(self.lab_connected)
    sb.addWidget(self.lab_disconnected)
    sb.addWidget(self.lab_port)
    sb.addWidget(separator(self.lab_home_warn))
    sb.addWidget(self.lab_home_warn)
    sb.addWidget(separator(self.lab_run))
    sb.addWidget(self.lab_run)
    self.setStatusBar(sb)

  def show_homepage(self):
    QDesktopServices.openUrl(APP_PAGE)

  def show_about(self):
    QMessageBox.about(self, APP_NAME, f"{APP_NAME}\nVersion: {APP_VERSION}")

  def show_about_qt(self):
    QMessageBox.aboutQt(self, APP_NAME)

  def board_command_beg(self, cmd: CMD):
    msg = board.get_cmd_run_text(cmd)
    log.debug(msg)
    self.update_actions()
    self.lab_run.setText(msg)
    self.lab_run.show()

  def board_command_end(self, cmd: CMD, err: str):
    self.update_actions()
    self.lab_run.hide()
    if cmd == CMD.connect or cmd == CMD.disconnect:
      self.show_connection()
    elif cmd == CMD.param and board.cmd_args_params_receive():
      QTimer.singleShot(0, self.edit_board_params)
    if err:
      QMessageBox.critical(self, APP_NAME, err)

  def show_connection(self):
    self.act_connect.setVisible(not board.connected)
    self.act_disconnect.setVisible(board.connected)
    self.lab_port.setText(f"{"Connected" if board.connected else "Disconnected"} {board.port()}")
    self.lab_connected.setVisible(board.connected)
    self.lab_disconnected.setVisible(not board.connected)
    if not board.connected:
      self.but_position_on.setFixedWidth(BUTTON_POS_MIN_W)
      self.but_position_off.setFixedWidth(BUTTON_POS_MIN_W)

  def show_position(self):
    pos = board.position
    text = "N/A" if pos is None else f"{pos}"
    fm = QFontMetrics(self.but_position_on.font())
    w = fm.size(0, text).width() + 2*BUTTON_POS_MARGIN
    if w > self.but_position_on.width():
      self.but_position_on.setFixedWidth(w)
      self.but_position_off.setFixedWidth(w)
    self.but_position_on.setText(text)
    self.but_position_off.setText(text)
    self.show_level()

  def show_level(self):
    log.debug(f"LEVEL:{board.level}")

  def update_actions(self):
    self.act_connect.setEnabled(board.can_connect and not board.connected)
    self.act_disconnect.setEnabled(board.can_connect and board.connected)
    self.act_board_params.setEnabled(board.can_home)
    self.act_home.setEnabled(board.can_home)
    self.act_stop.setEnabled(board.can_stop)
    self.act_move.setEnabled(board.can_move)
    self.act_get_position.setEnabled(board.can_move)
    self.act_jog_forth.setEnabled(board.can_jog)
    self.act_jog_forth_long.setEnabled(board.can_jog)
    self.act_jog_back.setEnabled(board.can_jog)
    self.act_jog_back_long.setEnabled(board.can_jog)
    self.act_scan.setEnabled(board.can_move)
    self.act_scans.setEnabled(board.can_move)
    self.act_position_on.setVisible(board.can_move)
    self.act_position_off.setVisible(not board.can_move)
    self.lab_home_warn.setVisible(board.connected and not board.homed)
    self.show_position()

  def go_to_position(self):
    if board.position is None:
      return
    old_pos = board.position
    (new_pos, ok) = QInputDialog.getDouble(self, APP_NAME, "Target position:", value=old_pos, step=0.1)
    if ok and int(new_pos*10) != int(old_pos*10):
      board.move(new_pos)

  def edit_board_params(self):
    changes = BoardParamsDialog(self).run()
    if changes:
      log.debug(f"changes:{changes}({len(changes)})")
      board.store_params(changes)
