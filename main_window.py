import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QStatusBar, QToolBar

from consts import APP_NAME, APP_VERSION, CMD_CONNECT, CMD_DISCONNECT, get_cmd_run_text
from plot import Plot
from utils import load_icon

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
  # Actions
  connect_action: QAction
  home_action: QAction
  stop_action: QAction

  # Status bar
  connect_label: QLabel
  port_label: QLabel
  status_label: QLabel

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
    self.home_action = self._a("Home", self.board.go_home, m, hotkey="Ctrl+H", icon="home")
    self.stop_action = self._a("Stop", self.board.stop_move, m, hotkey="Ctrl+B", icon="stop")
    m.addSeparator()
    self._a("Exit", self.close, m, hotkey="Ctrl+Q")

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
    self.addToolBar(Qt.LeftToolBarArea, tool_bar)

    tool_bar.addAction(self.connect_action)
    tool_bar.addSeparator()
    tool_bar.addAction(self.home_action)
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
