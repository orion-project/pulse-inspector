from enum import Enum
import logging
import numpy as np
from scipy.optimize import curve_fit
from collections import namedtuple
import os
from datetime import datetime
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget
from PySide6.QtCore import QStandardPaths

# There are tons of debug messages about found fonts
# that makes the global DEBUG level totally useless
logging.getLogger('matplotlib').level = logging.WARN
logging.getLogger('matplotlib.font_manager').level = logging.WARN

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.figure import Figure

from consts import APP_NAME, FitSubrangeMode
from utils import app_settings, calc_background_level
from fit_subrange_dialog import FitSubrangeDialog

Point = namedtuple('Point', 'x y')

class FIT(Enum):
  none = 0
  gauss = 1
  lorentz = 2
  sech2 = 3

LIGHT_SPEED = 0.299792458 # mkm/fs
ZOOM_FACTOR = 0.2 # zoom in/out factor per operation

log = logging.getLogger(__name__)

class Plot(FigureCanvas):
  fit_type = FIT.gauss
  show_delay = True
  show_norm = False
  x_data = None
  y_data = None
  _zoom_mode = "xy"
  _custom_lims_x = None
  _custom_lims_y = None
  _pan_start: Point|None = None
  _autosave = False
  _autosave_dir = ''
  _shift_fit_bgnd = True
  _fit_subrange = False
  _fit_subrange_mode = FitSubrangeMode.percent
  _fit_subrange_value: float = 10

  # To use as a parent for dialogs
  main_window: QWidget|None = None

  def __init__(self, parent=None):
    self.fig = Figure(figsize=(8, 6), dpi=100)
    self.axes = self.fig.add_subplot(111)
    self.fig.tight_layout(pad=4.0, w_pad=1.0, h_pad=1.0)
    super().__init__(self.fig)
    self.setParent(parent)

    self.mpl_connect('button_press_event', self._on_mouse_press)
    self.mpl_connect('motion_notify_event', self._on_mouse_move)
    self.mpl_connect('button_release_event', self._on_mouse_release)
    self.mpl_connect('scroll_event', self._on_mouse_scroll)

  def show_x_delay(self, on):
    self.show_delay = on
    self._replot()

  def show_y_norm(self, on):
    self.show_norm = on
    self._replot()

  def set_fit(self, fit_type: FIT):
    self.fit_type = fit_type
    self._replot()

  def set_shift_fit_bgnd(self, on):
    self._shift_fit_bgnd = on
    self._replot()

  def set_fit_subrange(self, on):
    self._fit_subrange = on
    self._replot()

  def open_graph(self, file_path: str):
    x, y = np.loadtxt(file_path, usecols=(0, 1), unpack=True)
    self.draw_graph(x, y, auto_save=False)

  def draw_graph(self, x, y, auto_save=True):
    self.x_data = np.array(x)
    self.y_data = np.array(y)
    self._replot()
    if auto_save:
      self._save_data_auto()

  def _is_empty(self):
    return self.x_data is None

  def _replot(self):
    self.axes.clear()

    # type-checker can't understand that it's the same as _is_empty()
    if self.x_data is None or self.y_data is None:
      return

    # For delay calculation we need to double the positions
    # When the stage shifts on a distance, the beam passes that distance back and forth
    self.xs = [*((self.x_data*2.0) if self.show_delay else self.x_data)]
    self.ys = self.y_data

    # Even when we hide the fit graph we still need to calc a fit
    # to find the peak center and calculate delay properly
    fit_params = self.fit_and_plot()
    if not fit_params: return

    if self._shift_fit_bgnd:
      self.y_fit += calc_background_level(self.ys)

    self.axes.plot(self.xs, self.ys, 'b-', linewidth=1.5, label="Experimental", alpha=0.7)
    if self.fit_type != FIT.none:
      self.axes.plot(self.x_fit, self.y_fit, 'r-', linewidth=2, label=fit_params["label"])
      self.show_fit_params(fit_params)
    self.axes.set_xlabel("Delay (fs)" if self.show_delay else "Position (um)")
    self.axes.set_ylabel("Intensity (a.u.)")
    #self.axes.set_title('')
    self.axes.grid(True, alpha=0.3)
    self.axes.legend()
    if self._custom_lims_x is not None:
      self.axes.set_xlim(*self._custom_lims_x)
    if self._custom_lims_y is not None:
      self.axes.set_ylim(*self._custom_lims_y)
    self.draw()

  def fit_and_plot(self):
    """
    Fits experimental data with a specified fit function,
    plots the fit curve and return fit parameters.
    """
    if self.xs is None or self.ys is None or len(self.xs) < 4:
        return None

    def gaussian(x, amplitude, center, width):
        return amplitude * np.exp(-(x - center)**2 / (2 * width**2))

    def lorentzian(x, amplitude, center, width):
        return amplitude / (1 + ((x - center) / width)**2)

    def sech_squared(x, amplitude, center, width):
        return amplitude / np.cosh((x - center) / width)**2

    if self.fit_type == FIT.gauss:
      fit_func = gaussian
      fit_label = "Gaussian Fit"
    elif self.fit_type == FIT.lorentz:
      fit_func = lorentzian
      fit_label = "Lorentzian Fit"
    else:
      fit_func = sech_squared
      fit_label = "sech² Fit"

    try:
      fit_xs = self.xs
      fit_ys = self.ys
      if self._fit_subrange:
        # Select central part of the source data for fitting
        i_beg = None
        i_end = None
        if self._fit_subrange_mode == FitSubrangeMode.percent:
          percent = min(max(self._fit_subrange_value, 1), 100)
          data_count = len(self.xs)
          i_beg = int(data_count * (100 - percent) / 200)
          i_end = int(data_count * (100 + percent) / 200)
        else:
          offset = abs(self._fit_subrange_value)
          if self._fit_subrange_mode == FitSubrangeMode.delay:
            # convert fs -> mkm (self.sx is always in mkm)
            offset *= LIGHT_SPEED
          for i in range(len(self.xs)):
            v = abs(self.xs[i])
            if i_beg is None:
              if v <= offset:
                i_beg = i
            elif v >= offset:
                i_end = i
                break
        if i_beg is not None and i_end is not None:
          fit_xs = self.xs[i_beg : i_end]
          fit_ys = self.ys[i_beg : i_end]

      amplitude_guess = np.max(fit_ys)
      center_guess = np.mean(fit_xs)
      width_guess = (np.max(fit_xs) - np.min(fit_xs)) / 6
      [amplitude, center, width], pcov = curve_fit(fit_func, fit_xs, fit_ys,
                            p0=[amplitude_guess, center_guess, width_guess],
                            maxfev=10000)

      if self.show_delay:
        # Convert positions in mkm to delays in fs
        self.xs = (self.xs - center) / LIGHT_SPEED
        center = 0.0
        width /= LIGHT_SPEED

      #x_fit = np.linspace(self.xs[0], self.xs[-1], len(self.xs))
      self.x_fit = self.xs
      self.y_fit = fit_func(self.x_fit, amplitude, center, width)

      if self.show_norm:
        if self.fit_type != FIT.none:
          max_y = np.max(self.y_fit)
          self.y_fit = self.y_fit / max_y
          self.ys = self.ys / max_y
        else:
          self.ys = self.ys / amplitude_guess

      return {
        "amplitude": amplitude,
        "center": center,
        "width": width,
        "label": fit_label,
      }
    except Exception as e:
      log.exception("fit")
      return None

  def show_fit_params(self, fit_params):
    """
    Display fit parameters and estimates pulse duration as text on the plot.
    Different fit types have different relationships between width parameter and FWHM.
    """
    if self.fit_type == FIT.gauss:
      # FWHM = 2 * sqrt(2 * ln(2)) * sigma
      fit_fwhm = 2.3548200450309493 * fit_params['width']
      deconvolution_factor = 1.4142135623730951 # sqrt(2)
    elif self.fit_type == FIT.lorentz:
      fit_fwhm = 2.0 * fit_params['width']
      deconvolution_factor = 1.4142135623730951 # sqrt(2)
    elif self.fit_type == FIT.sech2:
      # FWHM = 2 * ln(1 + sqrt(2)) * width
      fit_fwhm = 1.7627471740390859 * fit_params['width']
      deconvolution_factor = 1.543
    else:
      return

    pulse_duration = fit_fwhm / deconvolution_factor

    if self.show_delay:
      text = [
        f"Fit FWHM: {fit_fwhm:.2f} fs",
        f"Pulse duration: {pulse_duration:.2f} fs",
        #f"Amplitude: {fit_params['amplitude']:.2f} a.u."
      ]
    else:
      text = [
        f"Fit FWHM: {fit_fwhm:.2f} µm",
        f"Center: {fit_params['center']:.2f} µm",
        #f"Amplitude: {fit_params['amplitude']:.2f} a.u."
      ]
    self.axes.text(
      0.02,
      0.98,
      '\n'.join(text),
      transform=self.axes.transAxes,
      verticalalignment='top',
      horizontalalignment='left',
      #bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
      #fontsize=9,
      #family='monospace'
    )

  def set_zoom_mode(self, mode):
    self._zoom_mode = mode

  def _zoom(self, step, center_x=None, center_y=None):
    if self._is_empty():
      return

    factor = (1 - ZOOM_FACTOR) if step > 0 else (1 + ZOOM_FACTOR)

    def get_new_lim(old_lim, center):
      (c_pix, c_dat) = center
      (min_old, max_old) = old_lim
      range_old = max_old - min_old
      range_new = range_old * factor
      scale_old = c_pix / (c_dat - min_old)
      min_new = c_dat - c_pix * factor / scale_old
      return (min_new, min_new + range_new)

    if "x" in self._zoom_mode:
      self._custom_lims_x = get_new_lim(self.axes.get_xlim(), center_x)
      self.axes.set_xlim(*self._custom_lims_x)
    if "y" in self._zoom_mode:
      self._custom_lims_y = get_new_lim(self.axes.get_ylim(), center_y)
      self.axes.set_ylim(*self._custom_lims_y)
    self.draw()

  def reset_zoom(self):
    self._custom_lims_x = None
    self._custom_lims_y = None
    self._replot()

  def _on_mouse_press(self, event: MouseEvent):
    if self._is_empty():
      return
    if event.inaxes != self.axes:
      return
    if event.button == MouseButton.MIDDLE:
      x = float(event.x)
      y = float(event.y)
      if x is None or y is None: return
      self._pan_start = Point(x, y)

  def _on_mouse_move(self, event: MouseEvent):
    if not self._pan_start:
      return
    x = float(event.x)
    y = float(event.y)
    if x is None or y is None: return
    x_lim = self.axes.get_xlim()
    y_lim = self.axes.get_ylim()
    rect = self.axes.get_window_extent()
    x_scale = rect.width / (x_lim[1] - x_lim[0])
    y_scale = rect.height / (y_lim[1] - y_lim[0])
    dx = (self._pan_start.x - x) / x_scale
    dy = (self._pan_start.y - y) / y_scale
    self._pan_start = Point(x, y)
    self._custom_lims_x = x_lim + dx
    self._custom_lims_y = y_lim + dy
    self.axes.set_xlim(*self._custom_lims_x)
    self.axes.set_ylim(*self._custom_lims_y)
    self.draw()

  def _on_mouse_release(self, event: MouseEvent):
    if event.button == MouseButton.MIDDLE:
      self._pan_start = None

  def _on_mouse_scroll(self, event):
    if event.inaxes != self.axes:
      return
    self._zoom(event.step, center_x=(event.x, event.xdata), center_y=(event.y, event.ydata))

  def _calc_measured_fwhm(self):
    """
    Returns FWHM from measured data or None if it cannot be calculated.
    """
    if self.ys is None or self.xs is None or len(self.ys) < 3:
      return None

    try:
      # Find the maximum value and half maximum
      y_max = np.max(self.ys)
      half_max = y_max / 2.0

      # Find indices where y crosses half maximum
      # Use interpolation for better accuracy
      above_half = self.ys >= half_max

      # Find left crossing point
      left_idx = None
      for i in range(len(above_half) - 1):
        if not above_half[i] and above_half[i + 1]:
          # Interpolate
          left_idx = i + (half_max - self.ys[i]) / (self.ys[i + 1] - self.ys[i])
          break

      # Find right crossing point
      right_idx = None
      for i in range(len(above_half) - 1, 0, -1):
        if above_half[i - 1] and not above_half[i]:
          # Interpolate
          right_idx = i - 1 + (half_max - self.ys[i - 1]) / (self.ys[i] - self.ys[i - 1])
          break

      if left_idx is not None and right_idx is not None:
        # Calculate x positions using interpolated indices
        x_left = self.xs[int(left_idx)] + (left_idx - int(left_idx)) * (self.xs[int(left_idx) + 1] - self.xs[int(left_idx)])
        x_right = self.xs[int(right_idx)] + (right_idx - int(right_idx)) * (self.xs[int(right_idx) + 1] - self.xs[int(right_idx)])
        fwhm = abs(x_right - x_left)
        return fwhm

      return None

    except Exception as e:
      log.exception("Failed to calculate measured FWHM")
      return None

  def load_settings(self, s):
    self._autosave_dir = str(s.value("autosave_dir"))
    self._fit_subrange_mode = FitSubrangeMode[str(s.value("fit_subrange_mode", "percent"))]
    self._fit_subrange_value = float(s.value("fit_subrange_value", 10))
    # self._autosave is loaded in main window as part of generic options loading

  def set_autosave(self, on):
    log.info("Autosave " + ("enabled" if on else "disabled"))
    self._autosave = on

  def choose_autosave_dir(self):
    data_dir = QFileDialog.getExistingDirectory(
      self, APP_NAME, self._autosave_dir, QFileDialog.Option.ShowDirsOnly)
    if data_dir:
      self._autosave_dir = data_dir
      app_settings().setValue("autosave_dir", data_dir)
      log.info(f"Autosave dir is {data_dir}")

  def choose_fit_subrange(self):
    dlg = FitSubrangeDialog(self.main_window)
    res = dlg.run(self._fit_subrange_mode, self._fit_subrange_value)
    if res is not None:
      self._fit_subrange_mode = res[0]
      self._fit_subrange_value = res[1]
      s = app_settings()
      s.setValue("fit_subrange_mode", self._fit_subrange_mode.name)
      s.setValue("fit_subrange_value", self._fit_subrange_value)
      self._replot()

  def _make_data_filename(self, data_dir):
    timestamp = datetime.now().isoformat(timespec="milliseconds").replace(":", "-")
    return os.path.join(data_dir, f"ac_{timestamp}.txt")

  def _save_data(self, file_path, show_error=False):
    try:
      data = [self.xs, self.ys, self.y_fit] if self.fit_type != FIT.none else [self.xs, self.ys]
      np.savetxt(file_path, np.array(data).T)
      log.info(f"Data saved to {file_path}")
    except Exception as e:
      log.exception("Failed to save data")
      if show_error:
        QMessageBox.critical(self, APP_NAME, f"Failed to save data:\n{e}")

  def _save_data_auto(self):
    if not self._autosave or self._is_empty():
      return
    if not self._autosave_dir:
      data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
      data_dir = os.path.join(data_dir, "autocorrelation-measurements")
      if not os.path.exists(data_dir):
        try:
          os.mkdir(data_dir)
          log.info(f"Autosave dir created: {data_dir}")
        except Exception as e:
          log.exception("Failed to create autosave dir")
      else:
        log.info(f"Autosave dir exists: {data_dir}")
      self._autosave_dir = data_dir
    self._save_data(self._make_data_filename(self._autosave_dir))

  def save_data_dlg(self):
    """
    Show save file dialog and export plot data to a text file.
    """
    if self._is_empty():
      QMessageBox.warning(self, APP_NAME, "There is no data to save.")
      return

    s = app_settings()
    data_dir = s.value("data_dir")

    if not data_dir or not os.path.isdir(data_dir):
      data_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)

    file_path, _ = QFileDialog.getSaveFileName(
      self,
      "Save Plot Data",
      self._make_data_filename(data_dir),
      "Text Files (*.txt);;All Files (*.*)",
    )
    if file_path:
      s.setValue("data_dir", os.path.dirname(file_path))
      self._save_data(file_path, True)
