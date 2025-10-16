import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QStatusBar, QToolBar, QToolButton

from consts import APP_NAME, APP_VERSION, CMD_CONNECT, CMD_DISCONNECT, get_cmd_run_text
from plot import Plot
from utils import load_icon

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
  def __init__(self, board, dev_mode=False):
    super().__init__()

    self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

    self.dev_mode = dev_mode

    self.board = board
    self.board.on_command_beg.connect(self.board_command_beg)
    self.board.on_command_end.connect(self.board_command_end)

    self.create_menu_bar()
    self.create_tool_bar()
    self.create_status_bar()
    self.create_plot()

    self.show_board_connection()
    self.update_actions()

  def _a(self, title, handler, menu, **kwargs):
    a = QAction(title, self)
    a.triggered.connect(handler)
    if "hotkey" in kwargs:
      a.setShortcut(kwargs["hotkey"])
    if "icon" in kwargs:
      a.setIcon(load_icon(kwargs["icon"]))
    if menu:
      menu.addAction(a)
    return a

  def create_menu_bar(self):
    m = self.menuBar().addMenu("Board")
    self.connect_action = self._a("Connect", self.board.toggle_connection, m)
    self.connect_icon = load_icon("connect")
    self.disconnect_icon = load_icon("disconnect")
    m.addSeparator()
    self.home_action = self._a("Home", self.board.home, m, hotkey="Ctrl+H", icon="home")
    self.jog_backward_fast_action = self._a("Jog Backward (fast)", self.board.move, m, hotkey="Ctrl+Shift+Left", icon="jog_left_2")
    self.jog_backward_action = self._a("Jog Backward", self.board.move, m, hotkey="Ctrl+Left", icon="jog_left")
    self.move_action = self._a("Go To Position", self.board.move, m, hotkey="Ctrl+G", icon="walk")
    self.jog_forward_action = self._a("Jog Forward", self.board.move, m, hotkey="Ctrl+Right", icon="jog_right")
    self.jog_forward_fast_action = self._a("Jog Forward (fast)", self.board.move, m, hotkey="Ctrl+Shift+Right", icon="jog_right_2")
    self.stop_action = self._a("Stop", self.board.stop, m, hotkey="Ctrl+B", icon="stop")
    m.addSeparator()
    self._a("Exit", self.close, m, hotkey="Ctrl+Q")

    m = self.menuBar().addMenu("Measurement")
    self.measure_single_action = self._a("Single", self.board.move, m, hotkey="Ctrl+M", icon="photo")
    self.measure_single_action.setToolTip("Single Measurement")
    self.measure_cont_action = self._a("Continuous", self.board.move, m, hotkey="Ctrl+Shift+M", icon="video")
    self.measure_cont_action.setToolTip("Continuous Measurement")

    if self.dev_mode:
      m = self.menuBar().addMenu("Debug")
      self._a("Simulate disconnection", self.board.debug_simulate_disconnection, m)
      self._a("Simulate command error", self.board.debug_simulate_command_error, m)

    m = self.menuBar().addMenu('Help')
    self._a("About", self.show_about, m)
    self._a("About Qt", self.show_about_qt, m)

  def create_tool_bar(self):
    tool_bar = QToolBar("Main Toolbar")
    tool_bar.setIconSize(QSize(40, 40))
    tool_bar.setMovable(False)
    tool_bar.setFloatable(False)
    self.addToolBar(Qt.TopToolBarArea, tool_bar)

    self.position_button = QToolButton()
    self.position_button.setText("28.5")
    self.position_button.setToolTip("Current Position")

    tool_bar.addAction(self.connect_action)
    tool_bar.addSeparator()
    tool_bar.addAction(self.home_action)
    tool_bar.addAction(self.jog_backward_fast_action)
    tool_bar.addAction(self.jog_backward_action)
    tool_bar.addWidget(self.position_button)
    tool_bar.addAction(self.jog_forward_action)
    tool_bar.addAction(self.jog_forward_fast_action)
    tool_bar.addSeparator()
    tool_bar.addAction(self.measure_single_action)
    tool_bar.addAction(self.measure_cont_action)
    tool_bar.addSeparator()
    tool_bar.addAction(self.stop_action)

  def create_status_bar(self):
    status_bar = QStatusBar()
    self.setStatusBar(status_bar)

    self.connect_label = QLabel()
    self.connect_label.setContentsMargins(4, 0, 0, 0)
    self.connect_on_pxm = load_icon("lamp_green.svg").pixmap(16, 16)
    self.connect_off_pxm = load_icon("lamp_gray.svg").pixmap(16, 16)
    status_bar.addWidget(self.connect_label)

    self.port_label = QLabel()
    self.port_label.setContentsMargins(0, 0, 12, 2)
    status_bar.addWidget(self.port_label)

    self.status_label = QLabel()
    self.status_label.setContentsMargins(2, 0, 12, 2)
    status_bar.addWidget(self.status_label)

  def create_plot(self):
    self.plot = Plot(self)
    self.setCentralWidget(self.plot)
    self.plot.add_sample_graph()

  def show_about(self):
    QMessageBox.about(self, APP_NAME, f"{APP_NAME}\nVersion: {APP_VERSION}")

  def show_about_qt(self):
    QMessageBox.aboutQt(self, APP_NAME)

  def board_command_beg(self, cmd):
    msg = get_cmd_run_text(cmd)
    log.debug(msg)
    self.update_actions()
    self.status_label.setText(msg)

  def board_command_end(self, cmd, err):
    self.update_actions()
    self.status_label.setText(None)
    if cmd == CMD_CONNECT or cmd == CMD_DISCONNECT:
      self.show_board_connection()
    if err:
      QMessageBox.critical(self, APP_NAME, err)

  def show_board_connection(self):
    if self.board.connected:
      self.connect_label.setPixmap(self.connect_on_pxm)
      self.connect_action.setText("Disconnect")
      self.connect_action.setIcon(self.disconnect_icon)
      self.port_label.setText(f"{self.board.port()} connected")
    else:
      self.connect_label.setPixmap(self.connect_off_pxm)
      self.connect_action.setText("Connect")
      self.connect_action.setIcon(self.connect_icon)
      self.port_label.setText(f"{self.board.port()} disconnected")

  def update_actions(self):
    self.connect_action.setEnabled(self.board.can_connect)
    self.home_action.setEnabled(self.board.can_home)
    self.stop_action.setEnabled(self.board.can_stop)
    text_color = "#00547f" if self.board.can_move_abs else "gray"
    self.position_button.setStyleSheet(f"QToolButton{{font-size: 20px; font-weight: bold; color: {text_color};}}")
    self.position_button.setEnabled(self.board.can_move_abs)
    self.move_action.setEnabled(self.board.can_move_abs)
    self.jog_forward_action.setEnabled(self.board.can_move_rel)
    self.jog_forward_fast_action.setEnabled(self.board.can_move_rel)
    self.jog_backward_action.setEnabled(self.board.can_move_rel)
    self.jog_backward_fast_action.setEnabled(self.board.can_move_rel)
    self.measure_single_action.setEnabled(self.board.can_move_abs)
    self.measure_cont_action.setEnabled(self.board.can_move_abs)
