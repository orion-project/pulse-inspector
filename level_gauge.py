from PySide6.QtCore import QSettings

from linear_gauge import LinearGauge
from utils import app_settings, input_float_dlg

class LevelGauge:
  auto_max = True
  manual_max: float = 0.0

  def __init__(self):
    self.widget = LinearGauge()

  def set_value(self, v: float):
    self.widget.value = v
    if self.auto_max and v > self.widget.max_value:
      self.widget.max_value = self.widget.value
      self.widget.recalc_scale()
    self.widget.update()

  def use_auto_max(self, on: bool):
    self.auto_max = on
    if on:
      self.reset_auto_max()
    else:
      if self.manual_max > 0:
        self.widget.max_value = self.manual_max
      self.widget.recalc_scale()
      self.widget.update()

  def reset_auto_max(self):
    if self.auto_max:
      self.widget.max_value = self.widget.value
      self.widget.recalc_scale()
      self.widget.update()

  def choose_manual_max(self):
    value = input_float_dlg("Manual top limit:", self.manual_max)
    if value is None:
      return
    value = abs(value)
    if value == 0:
      return
    app_settings().setValue("gauge_manual_max", value)
    self.manual_max = value
    if not self.auto_max:
      self.widget.max_value = value
      self.widget.recalc_scale()
      self.widget.update()

  def load_settings(self, s: QSettings):
    self.manual_max = abs(float(str(s.value("gauge_manual_max", 0.0))))
    # self.auto_max is loaded in main window as part of generic options loading
    if not self.auto_max and self.manual_max > 0:
      self.widget.max_value = self.manual_max
    self.widget.prepare_draw()
    self.widget.recalc_scale()
