import math
from enum import Enum
from PySide6.QtCore import Qt, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFontMetrics
from PySide6.QtWidgets import QWidget

def calc_nice_scale(raw_min: float, raw_max: float, tick_count: int) -> tuple[float, float, float, float]:
  """
  Paul Heckbert's "Nice Numbers for Graph Labels" algorithm
  Calculate an initial raw tick spacing and convert to a "nice" clean spacing interval
  """
  raw_range = raw_max - raw_min
  if raw_range <= 0:
    return (0, 1, 0, 0)

  raw_spacing = raw_range / (tick_count - 1)
  exponent = math.floor(math.log10(raw_spacing))
  fraction = raw_spacing / (10 ** exponent)

  if fraction < 1.5:
    nice_fraction = 1.0
    minor_ticks = 5
  elif fraction < 2.25:
    nice_fraction = 2.0
    minor_ticks = 4
  elif fraction < 3.5:
    nice_fraction = 2.5
    minor_ticks = 5
  elif fraction < 7.5:
    nice_fraction = 5.0
    minor_ticks = 5
  else:
    nice_fraction = 10.0
    minor_ticks = 4

  major_tick_spacing = nice_fraction * (10 ** exponent)
  minor_tick_spacing = major_tick_spacing / minor_ticks

  # Adjust the bounds to snap perfectly to the nice intervals
  nice_min = math.floor(raw_min / major_tick_spacing) * major_tick_spacing
  nice_max = math.ceil(raw_max / major_tick_spacing) * major_tick_spacing

  return (nice_min, nice_max, major_tick_spacing, minor_tick_spacing)

class TickPosition(Enum):
  TOP = 0
  RIGHT = 1
  BOTTOM = 2
  LEFT = 3

class LinearGauge(QWidget):
  value: float = 0.0
  max_value: float = 100.0
  bar_size: int = 15
  margin_beg: int = 15
  margin_end: int = 15
  margin_side: int = 15
  border_width: float = 1
  border_radius: int = 0
  tick_count: int = 6
  tick_position = TickPosition.LEFT
  tick_margin: int = 0 # Distance between bar and ticks
  label_margin: int = 3 # Distance between ticks and labels
  label_size: int = 12
  major_tick_length: int = 6
  major_tick_width: float = 1
  minor_tick_length: int = 3
  minor_tick_width: float = 1
  show_debug_grid: bool = False
  back_color: QColor|None = QColor("#FFFFFF")
  bar_back_color = QColor("#E0E0E0")
  fill_color: QColor|None = None # If not set then use gradient
  fill_color_start = QColor("#00547f")
  fill_color_end = QColor("#0077FF")
  text_color = QColor("#2A2A2A")
  tick_color = QColor("#121212")
  min_auto_size: int = 80
  auto_size = True
  use_nice_max = True
  show_zero_tick = True

  _nice_max = 100.0
  _major_tick_spacing = 0.0
  _minor_tick_spacing = 0.0

  def __init__(self, parent=None):
    super().__init__(parent)

  def set_fixed_size(self, size: int):
    if self._is_vertical():
      self.setFixedWidth(size)
      self.setFixedHeight(16777215) # QWIDGETSIZE_MAX
    else:
      self.setFixedWidth(16777215) # QWIDGETSIZE_MAX
      self.setFixedHeight(size)

  def prepare_draw(self):
    if self.label_size > 0:
      self._label_font = self.font()
      self._label_font.setPixelSize(self.label_size)
      self._label_pen = QPen(self.text_color)

    self._bg_brush = QBrush(self.back_color) if self.back_color else None

    self._bar_pen = QPen(self.tick_color, self.border_width) \
      if self.border_width > 0 else QPen(Qt.PenStyle.NoPen)
    self._bar_brush = QBrush(self.bar_back_color)

    self.fill_brush = QBrush(self.fill_color) if self.fill_color else None

    self._major_tick_pen = QPen(self.tick_color, self.major_tick_width)
    self._minor_tick_pen = QPen(self.tick_color, self.minor_tick_width)

  def recalc_scale(self):
    _, self._nice_max, self._major_tick_spacing, self._minor_tick_spacing = \
      calc_nice_scale(0, self.max_value, self.tick_count)

    if self.auto_size:
      size = self.bar_size + self.tick_margin + self._tick_length() + 2*self.margin_side

      if self.label_size > 0 and self._major_tick_spacing > 0:
        size += self.label_margin

        if self._is_vertical():
          label_w = 0
          fm = QFontMetrics(self.font())
          tick = 0
          display_range, _ = self._get_display_range()
          while tick <= display_range:
            if (w := fm.boundingRect(self._format_label(tick)).width()) > label_w:
              label_w = w
            tick += self._major_tick_spacing
          size += label_w
        else:
          size += self.label_size

      self.set_fixed_size(max(self.min_auto_size, size))

  def _is_vertical(self):
    return self.tick_position == TickPosition.LEFT or self.tick_position == TickPosition.RIGHT

  def _tick_length(self):
    return max(self.major_tick_length, self.minor_tick_length)

  def _format_label(self, v: float) -> str:
    return "%g" % v

  def paintEvent(self, event):
    painter = QPainter(self)
    if self.border_radius > 0:
      painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if self._bg_brush:
      painter.fillRect(self.rect(), self._bg_brush)
    if self._is_vertical():
      self._draw_vertical_gauge(painter)
    else:
      self._draw_horizontal_gauge(painter)

  def _get_display_range(self) -> tuple[float, float]:
    display_range = self._nice_max if self.use_nice_max else self.max_value
    value = max(0, self.value)
    value_ratio = min(1, value / display_range)
    return (display_range, value_ratio)

  def _draw_vertical_gauge(self, painter):
    left_ticks = self.tick_position == TickPosition.LEFT
    w, h = self.width(), self.height()
    margin_top, margin_bot = self.margin_beg, self.margin_end
    bar_h = h - margin_top - margin_bot
    if left_ticks:
      bar_x = w - self.bar_size - self.margin_side
    else:
      bar_x = self.margin_side

    # Bar
    painter.setPen(self._bar_pen)
    painter.setBrush(self._bar_brush)
    self._draw_rect(painter, bar_x, margin_top, self.bar_size, bar_h)

    # Fill (Grows bottom to top)
    display_range, value_ratio = self._get_display_range()
    fill_h = bar_h * value_ratio

    if fill_h > 0:
      if self.fill_brush:
        painter.setBrush(self.fill_brush)
      else:
        gradient = QLinearGradient(bar_x, margin_top, bar_x, margin_top + bar_h)
        gradient.setColorAt(0.0, self.fill_color_end)
        gradient.setColorAt(1.0, self.fill_color_start)
        painter.setBrush(QBrush(gradient))
      self._draw_rect(painter, bar_x, margin_top + bar_h - fill_h, self.bar_size, fill_h)

    # Ticks and Labels
    if self._major_tick_spacing > 0:
      draw_major_ticks = self.major_tick_length > 0 and self.major_tick_width > 0
      if left_ticks:
        major_x1 = bar_x - self.tick_margin
        major_x2 = major_x1 - self.major_tick_length
      else:
        major_x1 = bar_x + self.bar_size + self.tick_margin
        major_x2 = major_x1 + self.major_tick_length

      draw_minor_ticks = self._minor_tick_spacing > 0 \
        and self.major_tick_length > 0 and self.minor_tick_width > 0
      minor_x1 = major_x1
      if left_ticks:
        minor_x2 = minor_x1 - self.minor_tick_length
      else:
        minor_x2 = minor_x1 + self.minor_tick_length

      draw_labels = self.label_size > 0
      if left_ticks:
        label_x = major_x2 - self.label_margin
        label_flags = Qt.AlignmentFlag.AlignVCenter + Qt.AlignmentFlag.AlignRight
      else:
        label_x = major_x2 + self.label_margin
        label_flags = Qt.AlignmentFlag.AlignVCenter + Qt.AlignmentFlag.AlignLeft
      label_flags += Qt.TextFlag.TextDontClip + Qt.TextFlag.TextSingleLine
      painter.setFont(self._label_font)

      def pixel(v: float) -> int:
        return margin_top + bar_h - int(v / display_range * bar_h)

      major_tick = 0
      while major_tick <= display_range:
        major_y = pixel(major_tick)
        if major_y < margin_top:
          break

        if draw_major_ticks:
          if self.show_zero_tick or major_tick > 0:
            painter.setPen(self._major_tick_pen)
            painter.drawLine(major_x1, major_y, major_x2, major_y)

          if draw_minor_ticks and major_tick < display_range:
            painter.setPen(self._minor_tick_pen)
            minor_tick = self._minor_tick_spacing
            while minor_tick < self._major_tick_spacing:
              minor_y = pixel(major_tick + minor_tick)
              if minor_y <= margin_top:
                break
              painter.drawLine(minor_x1, minor_y, minor_x2, minor_y)
              minor_tick += self._minor_tick_spacing

        if draw_labels and (self.show_zero_tick or major_tick > 0):
          painter.setPen(self._label_pen)
          painter.drawText(QRect(label_x, major_y, 0, 0),
                           label_flags, self._format_label(major_tick))

        major_tick += self._major_tick_spacing

    if self.show_debug_grid:
      painter.setPen(QPen(QColor("silver"), 1, Qt.PenStyle.DashLine))
      painter.setBrush(Qt.BrushStyle.NoBrush)
      painter.drawRect(0, 0, w-1, h-1);

  def _draw_horizontal_gauge(self, painter: QPainter):
    top_ticks = self.tick_position == TickPosition.TOP
    w, h = self.width(), self.height()
    margin_left, margin_right = self.margin_beg, self.margin_end
    bar_w = w - margin_left - margin_right
    full_h = self.bar_size + \
      self.tick_margin + self._tick_length() + \
      self.label_margin + self.label_size
    if top_ticks:
      bar_y = int((h + full_h)/2) - self.bar_size
    else:
      bar_y = int((h - full_h)/2)
    bar_right = margin_left + bar_w

    # Bar
    painter.setPen(self._bar_pen)
    painter.setBrush(self._bar_brush)
    self._draw_rect(painter, margin_left, bar_y, bar_w, self.bar_size)

    # Fill (Grows left to right)
    display_range, value_ratio = self._get_display_range()
    fill_w = bar_w * value_ratio

    if fill_w > 0:
      if self.fill_brush:
        painter.setBrush(self.fill_brush)
      else:
        gradient = QLinearGradient(margin_left, bar_y, margin_left + bar_w, bar_y)
        gradient.setColorAt(0.0, self.fill_color_start)
        gradient.setColorAt(1.0, self.fill_color_end)
        painter.setBrush(QBrush(gradient))
      self._draw_rect(painter, margin_left, bar_y, fill_w, self.bar_size)

    # Ticks and Labels
    if self._major_tick_spacing > 0:
      draw_major_ticks = self.major_tick_length > 0 and self.major_tick_width > 0
      if top_ticks:
        major_y1 = bar_y - self.tick_margin
        major_y2 = major_y1 - self.major_tick_length
      else:
        major_y1 = bar_y + self.bar_size + self.tick_margin
        major_y2 = major_y1 + self.major_tick_length

      draw_minor_ticks = self._minor_tick_spacing > 0 \
        and self.major_tick_length > 0 and self.minor_tick_width > 0
      minor_y1 = major_y1
      if top_ticks:
        minor_y2 = minor_y1 - self.minor_tick_length
      else:
        minor_y2 = minor_y1 + self.minor_tick_length

      draw_labels = self.label_size > 0
      if top_ticks:
        label_y = major_y2 - self.label_margin - self.label_size
        label_flags = Qt.AlignmentFlag.AlignHCenter + Qt.AlignmentFlag.AlignBottom
      else:
        label_y = major_y2 + self.label_margin
        label_flags = Qt.AlignmentFlag.AlignHCenter + Qt.AlignmentFlag.AlignTop
      label_flags += Qt.TextFlag.TextDontClip + Qt.TextFlag.TextSingleLine
      painter.setFont(self._label_font)

      def pixel(v: float) -> int:
        return margin_left + int(v / display_range * bar_w)

      major_tick = 0
      while major_tick <= display_range:
        major_x = pixel(major_tick)
        if major_x > bar_right:
          break

        if draw_major_ticks:
          if self.show_zero_tick or major_tick > 0:
            painter.setPen(self._major_tick_pen)
            painter.drawLine(major_x, major_y1, major_x, major_y2)

          if draw_minor_ticks and major_tick < display_range:
            painter.setPen(self._minor_tick_pen)
            minor_tick = self._minor_tick_spacing
            while minor_tick < self._major_tick_spacing:
              minor_x = pixel(major_tick + minor_tick)
              if minor_x >= bar_right:
                break
              painter.drawLine(minor_x, minor_y1, minor_x, minor_y2)
              minor_tick += self._minor_tick_spacing

        if draw_labels and (self.show_zero_tick or major_tick > 0):
          painter.setPen(self._label_pen)
          painter.drawText(QRect(major_x, label_y, 0, self.label_size),
                           label_flags, self._format_label(major_tick))

        major_tick += self._major_tick_spacing

    if self.show_debug_grid:
      painter.setPen(QPen(QColor("silver"), 1, Qt.PenStyle.DashLine))
      painter.setBrush(Qt.BrushStyle.NoBrush)
      painter.drawRect(0, 0, w-1, h-1);
      painter.drawLine(0, int(h/2), w, int(h/2))
      painter.drawLine(0, int((h+full_h)/2), w, int((h+full_h)/2))
      painter.drawLine(0, int((h-full_h)/2), w, int((h-full_h)/2))

  def _draw_rect(self, painter: QPainter, x: float, y: float, w: float, h: float):
    rect = QRectF(x, y, w, h)
    if self.border_radius > 0:
      painter.drawRoundedRect(rect, self.border_radius, self.border_radius)
    else:
      painter.drawRect(rect)

if __name__ == "__main__":
  import sys
  from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, \
      QSpinBox, QPushButton, QCheckBox, QLineEdit, QSlider

  class DemoWindow(QWidget):
    def __init__(self):
      super().__init__()
      self.setWindowTitle("Linear Gauge Demo")

      self.gauges: dict[str, LinearGauge] = {}

      gauge = LinearGauge()
      gauge.tick_position = TickPosition.TOP
      self.gauges["top"] = gauge

      gauge = LinearGauge()
      gauge.tick_position = TickPosition.BOTTOM
      gauge.fill_color = QColor("#00547f")
      self.gauges["bottom"] = gauge

      gauge = LinearGauge()
      gauge.tick_position = TickPosition.RIGHT
      self.gauges["right"] = gauge

      gauge = LinearGauge()
      gauge.tick_position = TickPosition.LEFT
      gauge.fill_color_start = QColor("#00FFCC")
      self.gauges["left"] = gauge

      for g in self.gauges.values():
        g.prepare_draw()
        g.recalc_scale()

      self.slider = QSlider(Qt.Orientation.Horizontal)
      self.slider.setRange(0, int(gauge.max_value))
      self.slider.valueChanged.connect(self.apply_value)

      props_layout = QFormLayout()

      self.prop_editors: dict[str, QWidget] = {}

      def prop_bool(prop: str):
        ed = QCheckBox()
        ed.setChecked(bool(getattr(gauge, prop)))
        props_layout.addRow(prop, ed)
        self.prop_editors[prop] = ed

      def prop_int(prop: str, min: int, max: int):
        ed = QSpinBox()
        ed.setMinimum(min)
        ed.setMaximum(max)
        if hasattr(gauge, prop):
          ed.setValue(int(getattr(gauge, prop)))
        props_layout.addRow(prop, ed)
        self.prop_editors[prop] = ed

      def prop_float(prop: str):
        ed = QLineEdit()
        ed.setText(str(getattr(gauge, prop)))
        props_layout.addRow(prop, ed)
        self.prop_editors[prop] = ed

      prop_float("max_value")
      prop_bool("use_nice_max")
      prop_int("bar_size", 0, 50)
      prop_int("widget_size", 0, 500)
      prop_int("min_auto_size", 0, 500)
      prop_int("margin_beg", 0, 50)
      prop_int("margin_end", 0, 50)
      prop_int("margin_side", 0, 20)
      prop_float("border_width")
      prop_int("border_radius", 0, 10)
      prop_int("tick_count", 2, 20)
      prop_int("tick_margin", 0, 10)
      prop_bool("show_zero_tick")
      prop_int("label_margin", 0, 10)
      prop_int("label_size", 0, 40)
      prop_int("major_tick_length", 0, 20)
      prop_float("major_tick_width")
      prop_int("minor_tick_length", 0, 20)
      prop_float("minor_tick_width")
      prop_bool("show_debug_grid")

      but_apply = QPushButton("Apply")
      but_apply.clicked.connect(self.apply_props)
      props_layout.addWidget(but_apply)

      layout1 = QHBoxLayout()
      layout1.addLayout(props_layout)
      layout1.addSpacing(50)
      layout1.addWidget(self.gauges["right"])
      layout1.addWidget(self.gauges["left"])

      main_layout = QVBoxLayout(self)
      main_layout.addWidget(self.slider)
      main_layout.addWidget(self.gauges["top"])
      main_layout.addWidget(self.gauges["bottom"])
      main_layout.addLayout(layout1)

    def apply_value(self):
      for g in self.gauges.values():
        g.value = self.slider.value()
        g.update()

    def apply_props(self):
      for g in self.gauges.values():
        for prop in self.prop_editors:
          value = None
          editor = self.prop_editors[prop]
          match editor:
            case QSpinBox():
              value = editor.value()
            case QCheckBox():
              value = editor.isChecked()
            case QLineEdit():
              value = float(editor.text())
          if value is None:
            continue
          if prop == "widget_size":
            size = int(value)
            g.auto_size = size == 0
            if not g.auto_size:
              g.set_fixed_size(size)
            continue
          setattr(g, prop, value)
          if prop == "max_value":
            if g.value > g.max_value:
              g.value = g.max_value
            self.slider.setMaximum(int(g.max_value))
            self.slider.setValue(int(g.value))
        g.prepare_draw()
        g.recalc_scale()
        g.update()

  app = QApplication(sys.argv)
  app.setStyle("fusion")
  window = DemoWindow()
  window.show()
  sys.exit(app.exec())
