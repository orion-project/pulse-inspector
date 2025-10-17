import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices
from PySide6.QtWidgets import (
  QLabel, QMainWindow, QMessageBox, QStatusBar, QToolBar, QToolButton, QInputDialog)

from board import board
from consts import APP_NAME, APP_VERSION, APP_PAGE, CMD, get_cmd_run_text
from plot import Plot
from utils import load_icon, make_sample_profile

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
  action_groups = {}

  def __init__(self, dev_mode=False):
    super().__init__()

    self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

    self.dev_mode = dev_mode

    self.create_plot()
    self.create_menu_bar()
    self.create_tool_bar()
    self.create_status_bar()

    board.on_command_beg.connect(self.board_command_beg)
    board.on_command_end.connect(self.board_command_end)
    board.on_data_received.connect(self.plot.draw_graph)
    board.on_stage_moved.connect(self.show_position)

    self.show_board_connection()
    self.update_actions()

  def create_menu_bar(self):

    def A(title, handler, menu, **kwargs):
      a = QAction(title, self)
      a.triggered.connect(handler)
      if "key" in kwargs:
        a.setShortcut(kwargs["key"])
      if "icon" in kwargs:
        a.setIcon(load_icon(kwargs["icon"]))
      if "group" in kwargs:
        name = kwargs["group"]
        group = self.action_groups.get(name)
        if not group:
          group = QActionGroup(self)
          group.setExclusive(True)
          self.action_groups[name] = group
        a.setCheckable(True)
        a.setActionGroup(group)
      if "checked" in kwargs:
        a.setCheckable(True)
        a.setChecked(kwargs["checked"])
      if menu:
        menu.addAction(a)
      return a

    m = self.menuBar().addMenu("Board")
    self.act_connect = A("Connect", board.toggle_connection, m)
    self.connect_icon = load_icon("connect")
    self.disconnect_icon = load_icon("disconnect")
    m.addSeparator()
    self.act_config = A("Configuration... (TBD)", board.toggle_connection, m, icon="chip")
    self.act_config.setEnabled(False)
    m.addSeparator()
    A("Exit", self.close, m, key="Ctrl+Q")

    m = self.menuBar().addMenu("Move")
    self.act_home = A("Home", board.home, m, key="Ctrl+H", icon="home")
    m.addSeparator()
    self.act_jog_back_long = A("Jog Backward (long)", board.jog_back_long, m, key="Ctrl+Shift+Left", icon="jog_left_2")
    self.act_jog_back = A("Jog Backward", board.jog_back, m, key="Ctrl+Left", icon="jog_left")
    self.act_move = A("Go To Position...", self.do_move, m, key="Ctrl+G", icon="walk")
    self.act_jog_forth = A("Jog Forward", board.jog_forth, m, key="Ctrl+Right", icon="jog_right")
    self.act_jog_forth_long = A("Jog Forward (long)", board.jog_forth_long, m, key="Ctrl+Shift+Right", icon="jog_right_2")
    m.addSeparator()
    self.act_stop = A("Stop", board.stop, m, key="Ctrl+B", icon="stop")

    m = self.menuBar().addMenu("Scan")
    self.act_scan = A("Single", board.scan, m, key="F5", icon="photo")
    self.act_scan.setToolTip("Single Scan")
    self.act_scans = A("Continuous", board.scans, m, key="F9", icon="video")
    self.act_scans.setToolTip("Continuous Scanning")
    m.addSeparator()
    A("Show Delay", self.plot.show_as_delay, m, group="scan", checked=True)
    A("Show Position", self.plot.show_as_pos, m, group="scan")
    m.addSeparator()
    A("Gaussian Fit", self.plot.fit_gauss, m, group="fit", checked=True)
    A("Lorentzian Fit", self.plot.fit_lorentz, m, group="fit")
    A("sech² Fit", self.plot.fit_sech2, m, group="fit")

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
    tb = QToolBar("Main Toolbar")
    tb.setIconSize(QSize(40, 40))
    tb.setMovable(False)
    tb.setFloatable(False)
    self.addToolBar(Qt.TopToolBarArea, tb)

    self.but_move = QToolButton()
    self.but_move.setToolTip("Current Position")
    self.but_move.clicked.connect(self.do_move)

    tb.addAction(self.act_connect)
    tb.addSeparator()
    tb.addAction(self.act_home)
    tb.addAction(self.act_jog_back_long)
    tb.addAction(self.act_jog_back)
    tb.addWidget(self.but_move)
    tb.addAction(self.act_jog_forth)
    tb.addAction(self.act_jog_forth_long)
    tb.addSeparator()
    tb.addAction(self.act_scan)
    tb.addAction(self.act_scans)
    tb.addSeparator()
    tb.addAction(self.act_stop)

  def create_status_bar(self):
    sb = QStatusBar()
    self.setStatusBar(sb)

    self.lab_connect = QLabel()
    self.lab_connect.setContentsMargins(4, 0, 0, 0)
    self.pxm_on = load_icon("lamp_green").pixmap(16, 16)
    self.pxm_off = load_icon("lamp_gray").pixmap(16, 16)
    sb.addWidget(self.lab_connect)

    self.lab_port = QLabel()
    self.lab_port.setContentsMargins(0, 0, 12, 2)
    sb.addWidget(self.lab_port)

    self.lab_run = QLabel()
    self.lab_run.setContentsMargins(2, 0, 12, 2)
    sb.addWidget(self.lab_run)

  def create_plot(self):
    self.plot = Plot(self)
    self.setCentralWidget(self.plot)
    self.plot.draw_graph(*make_sample_profile())

  def show_homepage(self):
    QDesktopServices.openUrl(APP_PAGE)

  def show_about(self):
    QMessageBox.about(self, APP_NAME, f"{APP_NAME}\nVersion: {APP_VERSION}")

  def show_about_qt(self):
    QMessageBox.aboutQt(self, APP_NAME)

  def board_command_beg(self, cmd: CMD):
    msg = get_cmd_run_text(cmd)
    log.debug(msg)
    self.update_actions()
    self.lab_run.setText(msg)

  def board_command_end(self, cmd: CMD, err: str):
    self.update_actions()
    self.lab_run.setText(None)
    if cmd == CMD.connect or cmd == CMD.disconnect:
      self.show_board_connection()
    if err:
      QMessageBox.critical(self, APP_NAME, err)

  def show_board_connection(self):
    if board.connected:
      self.lab_connect.setPixmap(self.pxm_on)
      self.act_connect.setText("Disconnect")
      self.act_connect.setIcon(self.disconnect_icon)
      self.lab_port.setText(f"{board.port()} connected")
    else:
      self.lab_connect.setPixmap(self.pxm_off)
      self.act_connect.setText("Connect")
      self.act_connect.setIcon(self.connect_icon)
      self.lab_port.setText(f"{board.port()} disconnected")

  def show_position(self):
    pos = board.position
    self.but_move.setText("N/A" if pos is None else f"{pos}" )

  def update_actions(self):
    self.act_connect.setEnabled(board.can_connect)
    self.act_home.setEnabled(board.can_home)
    self.act_stop.setEnabled(board.can_stop)
    self.act_move.setEnabled(board.can_move)
    self.act_jog_forth.setEnabled(board.can_jog)
    self.act_jog_forth_long.setEnabled(board.can_jog)
    self.act_jog_back.setEnabled(board.can_jog)
    self.act_jog_back_long.setEnabled(board.can_jog)
    self.act_scan.setEnabled(board.can_move)
    self.act_scans.setEnabled(board.can_move)

    text_color = "#00547f" if board.can_move else "gray"
    self.but_move.setStyleSheet(f"QToolButton{{font-size: 20px; font-weight: bold; color: {text_color};}}")
    self.but_move.setEnabled(board.can_move)
    self.show_position()

  def do_move(self):
    old_pos = board.position
    (new_pos, ok) = QInputDialog.getDouble(self, APP_NAME, "Target position:", value=old_pos, step=0.1)
    if ok and int(new_pos*10) != int(old_pos*10):
      board.move(new_pos)
