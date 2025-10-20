from enum import Enum

APP_NAME = "Pulse Inspector"
APP_VERSION = "0.0.1"
APP_PAGE = "https://github.com/orion-project/pulse-inspector"

class CMD(Enum):
  connect = "CONNECT"
  disconnect = "DISCONNECT"
  home = "HOME"
  stop = "STOP"
  move = "MOVE"
  jog = "JOG"
  scan = "SCAN"
  scans = "SCANS"
  param = "PARAM"
  error = "ERROR"
