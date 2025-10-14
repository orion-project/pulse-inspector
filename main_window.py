from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QMainWindow, QMessageBox, QStatusBar

from consts import APP_NAME, APP_VERSION
from utils import load_icon

class MainWindow(QMainWindow):
  # Actions
  connect_action: QAction

  # Status bar
  connect_label: QLabel
  port_label: QLabel
  status_label: QLabel

  def __init__(self, board, dev_mode=False):
    super().__init__()

    self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")

    self.dev_mode = dev_mode

    self.board = board
    self.board.on_status.connect(self.show_board_status)
    self.board.on_error.connect(self.show_board_error)
    self.board.on_connect.connect(self.show_board_connection)

    self.create_menu_bar()
    self.create_status_bar()

    self.show_board_connection()

  def _a(self, title, handler, menu, **kwargs):
    a = QAction(title, self)
    a.triggered.connect(handler)
    if "hotkey" in kwargs:
      a.setShortcut(kwargs["hotkey"])
    if menu:
      menu.addAction(a)
    return a

  def create_menu_bar(self):
    m = self.menuBar().addMenu("Board")
    self.connect_action = self._a("Connect", self.board.toggle_connection, m)
    m.addSeparator()
    self._a("Exit", self.close, m, hotkey="Ctrl+Q")

    if self.dev_mode:
      m = self.menuBar().addMenu("Debug")

      if self.board.port() == "VIRTUAL":
        self._a("Simulate disconnection", self.board.debug_simulate_disconnection, m)

    m = self.menuBar().addMenu('Help')
    self._a("About", self.show_about, m)
    self._a("About Qt", self.show_about_qt, m)

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

  def show_about(self):
    QMessageBox.about(self, APP_NAME, f"{APP_NAME}\nVersion: {APP_VERSION}")

  def show_about_qt(self):
    QMessageBox.aboutQt(self, APP_NAME)

  def show_board_status(self, msg):
    if msg:
      print(msg)
    self.status_label.setText(msg)

  def show_board_error(self, cmd, msg):
    self.status_label.setText(None)
    print(f"Failed to process command {cmd}: {msg}")
    QMessageBox.critical(self, APP_NAME, msg)

  def show_board_connection(self):
    if self.board.connected:
      self.connect_label.setPixmap(self.connect_on_pxm)
      self.connect_action.setText("Disconnect")
      msg = f"{self.board.port()} connected"
    else:
      self.connect_label.setPixmap(self.connect_off_pxm)
      self.connect_action.setText("Connect")
      msg = f"{self.board.port()} disconnected"
    self.status_label.setText(None)
    self.port_label.setText(msg)
    print(msg)
