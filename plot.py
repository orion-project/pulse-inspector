from enum import Enum
import logging
import numpy as np
from scipy.optimize import curve_fit
from collections import namedtuple

# There are tons of debug messages about found fonts
# that makes the global DEBUG level totally useless
logging.getLogger('matplotlib').level = logging.WARN
logging.getLogger('matplotlib.font_manager').level = logging.WARN

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backend_bases import MouseButton, MouseEvent
from matplotlib.figure import Figure

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
  _pan_start: Point = None

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

  def show_x_pos(self):
    self.show_delay = False
    self._replot()

  def show_x_delay(self):
    self.show_delay = True
    self._replot()

  def show_y_raw(self):
    self.show_norm = False
    self._replot()

  def show_y_norm(self):
    self.show_norm = True
    self._replot()

  def fit_none(self):
    self.fit_type = FIT.none
    self._replot()

  def fit_gauss(self):
    self.fit_type = FIT.gauss
    self._replot()

  def fit_lorentz(self):
    self.fit_type = FIT.lorentz
    self._replot()

  def fit_sech2(self):
    self.fit_type = FIT.sech2
    self._replot()

  def draw_graph(self, x, y):
    self.x_data = np.array(x)
    self.y_data = np.array(y)
    self._replot()

  def _is_empty(self):
    return self.x_data is None

  def _replot(self):
    self.axes.clear()

    if self._is_empty():
      return

    # For delay calculation we need to double the positions
    # When the stage shifts on a distance, the beam passes that distance back and forth
    self.xs = [*((self.x_data*2.0) if self.show_delay else self.x_data)]
    self.ys = self.y_data

    # Even when we hide the fit graph we still need to calc a fit
    # to find the peak center and calculate delay properly
    fit_params = self.fit_and_plot()
    if not fit_params: return

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
      amplitude_guess = np.max(self.ys)
      center_guess = np.mean(self.xs)
      width_guess = (np.max(self.xs) - np.min(self.xs)) / 6
      [amplitude, center, width], pcov = curve_fit(fit_func, self.xs, self.ys,
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
          max = np.max(self.y_fit)
          self.y_fit = self.y_fit / max
          self.ys = self.ys / max
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

  def set_zoom_x(self):
    self._zoom_mode = "x"

  def set_zoom_y(self):
    self._zoom_mode = "y"

  def set_zoom_xy(self):
    self._zoom_mode = "xy"

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
