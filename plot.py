import logging
import numpy as np
from scipy.optimize import curve_fit

# There are tons of debug messages about found fonts
# that makes the global DEBUG level totally useless
logging.getLogger('matplotlib').level = logging.WARN
logging.getLogger('matplotlib.font_manager').level = logging.WARN

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

FIT_GAUSS = "gauss"
FIT_LORENTZ = "lorentz"
FIT_SECH2 = "sech2"

log = logging.getLogger(__name__)

class Plot(FigureCanvas):
  fit_type = FIT_GAUSS

  def __init__(self, parent=None):
    self.fig = Figure(figsize=(8, 6), dpi=100)
    self.axes = self.fig.add_subplot(111)
    self.fig.tight_layout(pad=3.0, w_pad=1.0, h_pad=1.0)
    super().__init__(self.fig)
    self.setParent(parent)

    # Store current data
    self.xs = None
    self.ys = None

  def draw_graph(self, x, y):
    self.xs = x
    self.ys = y

    self.axes.clear()
    self.axes.plot(self.xs, self.ys, 'b-', linewidth=1.5, label="Experimental", alpha=0.7)

    fit_params = self.fit_and_plot()
    if fit_params:
      self.show_fit_params(fit_params, self.fit_type)

    self.axes.set_xlabel("Delay (fs)")
    self.axes.set_ylabel("Intensity (a.u.)")
    #self.axes.set_title('')
    self.axes.grid(True, alpha=0.3)
    self.axes.legend()

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

    if self.fit_type == FIT_GAUSS:
      fit_func = gaussian
      fit_label = "Gaussian Fit"
    elif self.fit_type == FIT_LORENTZ:
      fit_func = lorentzian
      fit_label = "Lorentzian Fit"
    elif self.fit_type == FIT_SECH2:
      fit_func = sech_squared
      fit_label = "sech² Fit"
    else:
        return None

    try:
      amplitude_guess = np.max(self.ys)
      center_guess = np.mean(self.xs)
      width_guess = (np.max(self.xs) - np.min(self.xs)) / 6
      popt, pcov = curve_fit(fit_func, self.xs, self.ys,
                            p0=[amplitude_guess, center_guess, width_guess],
                            maxfev=10000)

      x_fit = np.linspace(self.xs[0], self.xs[-1], len(self.xs))
      y_fit = fit_func(x_fit, *popt)
      self.axes.plot(x_fit, y_fit, 'r-', linewidth=2, label=fit_label)

      return {
        'amplitude': popt[0],
        'center': popt[1],
        'width': popt[2]
      }

    except Exception as e:
      log.exception("fit")
      return None

  def show_fit_params(self, fit_params, fit_type):
    """
    Display fit parameters and estimates pulse duration as text on the plot.
    Different fit types have different relationships between width parameter and FWHM.
    """
    #measured_fwhm = self._calc_measured_fwhm()

    if fit_type == FIT_GAUSS:
      # FWHM = 2 * sqrt(2 * ln(2)) * sigma
      fit_fwhm = 2.3548200450309493 * fit_params['width']
      deconvolution_factor = 1.4142135623730951 # sqrt(2)
    elif fit_type == FIT_LORENTZ:
      fit_fwhm = 2.0 * fit_params['width']
      deconvolution_factor = 1.4142135623730951 # sqrt(2)
    elif fit_type == FIT_SECH2:
      # FWHM = 2 * ln(1 + sqrt(2)) * width
      fit_fwhm = 1.7627471740390859 * fit_params['width']
      deconvolution_factor = 1.543
    else:
      return

    pulse_duration = fit_fwhm / deconvolution_factor

    text = [
      f"Pulse duration: {pulse_duration:.2f} fs",
      f"Fit FWHM: {fit_fwhm:.2f} fs",
      #f"Measured FWHM: {measured_fwhm:.2f} fs" if measured_fwhm else "Measured FWHM: N/A",
      #f"Center: {fit_params['center']:.2f} fs",
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
