import logging
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QStatusBar, QToolBar, QToolButton, QInputDialog

from board import board
from consts import APP_NAME, APP_VERSION, CMD, get_cmd_run_text
from plot import Plot
from utils import load_icon

log = logging.getLogger(__name__)

class MainWindow(QMainWindow):
  def __init__(self, dev_mode=False):
    super().__init__()

    self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

    self.dev_mode = dev_mode

    board.on_command_beg.connect(self.board_command_beg)
    board.on_command_end.connect(self.board_command_end)

    self.create_menu_bar()
    self.create_tool_bar()
    self.create_status_bar()
    self.create_plot()

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
      if menu:
        menu.addAction(a)
      return a

    m = self.menuBar().addMenu("Board")
    self.connect_action = A("Connect", board.toggle_connection, m)
    self.connect_icon = load_icon("connect")
    self.disconnect_icon = load_icon("disconnect")
    m.addSeparator()
    self.home_action = A("Home", board.home, m, key="Ctrl+H", icon="home")
    self.jog_backward_fast_action = A("Jog Backward (fast)", board.move, m, key="Ctrl+Shift+Left", icon="jog_left_2")
    self.jog_backward_action = A("Jog Backward", board.move, m, key="Ctrl+Left", icon="jog_left")
    self.move_action = A("Go To Position", self.do_move, m, key="Ctrl+G", icon="walk")
    self.jog_forward_action = A("Jog Forward", board.move, m, key="Ctrl+Right", icon="jog_right")
    self.jog_forward_fast_action = A("Jog Forward (fast)", board.move, m, key="Ctrl+Shift+Right", icon="jog_right_2")
    self.stop_action = A("Stop", board.stop, m, key="Ctrl+B", icon="stop")
    m.addSeparator()
    A("Exit", self.close, m, key="Ctrl+Q")

    m = self.menuBar().addMenu("Measurement")
    self.measure_single_action = A("Single", board.move, m, key="Ctrl+M", icon="photo")
    self.measure_single_action.setToolTip("Single Measurement")
    self.measure_cont_action = A("Continuous", board.move, m, key="Ctrl+Shift+M", icon="video")
    self.measure_cont_action.setToolTip("Continuous Measurement")

    if self.dev_mode:
      m = self.menuBar().addMenu("Debug")
      A("Simulate disconnection", board.debug_simulate_disconnection, m)
      A("Simulate command error", board.debug_simulate_command_error, m)

    m = self.menuBar().addMenu('Help')
    A("About", self.show_about, m)
    A("About Qt", self.show_about_qt, m)

  def create_tool_bar(self):
    tool_bar = QToolBar("Main Toolbar")
    tool_bar.setIconSize(QSize(40, 40))
    tool_bar.setMovable(False)
    tool_bar.setFloatable(False)
    self.addToolBar(Qt.TopToolBarArea, tool_bar)

    self.position_button = QToolButton()
    self.position_button.setToolTip("Current Position")
    self.position_button.clicked.connect(self.do_move)

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

  def board_command_beg(self, cmd: CMD):
    msg = get_cmd_run_text(cmd)
    log.debug(msg)
    self.update_actions()
    self.status_label.setText(msg)

  def board_command_end(self, cmd: CMD, err: str):
    self.update_actions()
    self.status_label.setText(None)
    if cmd == CMD.connect or cmd == CMD.disconnect:
      self.show_board_connection()
    if err:
      QMessageBox.critical(self, APP_NAME, err)

  def show_board_connection(self):
    if board.connected:
      self.connect_label.setPixmap(self.connect_on_pxm)
      self.connect_action.setText("Disconnect")
      self.connect_action.setIcon(self.disconnect_icon)
      self.port_label.setText(f"{board.port()} connected")
    else:
      self.connect_label.setPixmap(self.connect_off_pxm)
      self.connect_action.setText("Connect")
      self.connect_action.setIcon(self.connect_icon)
      self.port_label.setText(f"{board.port()} disconnected")

  def update_actions(self):
    self.connect_action.setEnabled(board.can_connect)
    self.home_action.setEnabled(board.can_home)
    self.stop_action.setEnabled(board.can_stop)
    self.move_action.setEnabled(board.can_move)
    self.jog_forward_action.setEnabled(board.can_jog)
    self.jog_forward_fast_action.setEnabled(board.can_jog)
    self.jog_backward_action.setEnabled(board.can_jog)
    self.jog_backward_fast_action.setEnabled(board.can_jog)
    self.measure_single_action.setEnabled(board.can_move)
    self.measure_cont_action.setEnabled(board.can_move)

    text_color = "#00547f" if board.can_move else "gray"
    self.position_button.setStyleSheet(f"QToolButton{{font-size: 20px; font-weight: bold; color: {text_color};}}")
    self.position_button.setEnabled(board.can_move)
    self.position_button.setText("N/A" if board.position is None else f"{board.position}" )

  def do_move(self):
    old_pos = board.position
    (new_pos, ok) = QInputDialog.getDouble(self, APP_NAME, "Target position:", value=old_pos, step=0.1)
    if ok and int(new_pos*10) != int(old_pos*10):
      board.move(new_pos)
