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
  def __init__(self, parent=None, width=8, height=6, dpi=100):
    self.fig = Figure(figsize=(width, height), dpi=dpi)
    self.axes = self.fig.add_subplot(111)
    self.fig.tight_layout(pad=2.0, w_pad=1.0, h_pad=1.0)
    super().__init__(self.fig)
    self.setParent(parent)

    # Store current data
    self.x_data = None
    self.y_data = None

  def add_sample_graph(self):
    """
    Plot sample profile graph with noise and fit
    """
    self.axes.clear()

    x_min = -100
    x_max = 100
    y_max = 10
    stdev = 30
    num_points = 201
    noise_level = 0.05
    fit_type = FIT_GAUSS

    self.x_data = np.linspace(x_min, x_max, num_points)
    profile = y_max * np.exp(-(self.x_data**2) / (2 * stdev**2))
    noise = np.random.normal(0, y_max * noise_level, num_points)
    self.y_data = profile + noise
    self.axes.plot(self.x_data, self.y_data, 'b-', linewidth=1.5, label="Experimental", alpha=0.7)

    fit_params = self.fit_and_plot(fit_type, num_points)
    if fit_params:
      self.show_fit_params(fit_params)

    self.axes.set_xlabel("Delay (fs)")
    self.axes.set_ylabel("Intensity (a.u.)")
    #self.axes.set_title('')
    self.axes.grid(True, alpha=0.3)
    self.axes.legend()

    self.draw()

  def fit_and_plot(self, fit_type, num_points):
    """
    Fits experimental data with a specified fit function,
    plots the fit curve and return fit parameters.
    """
    if self.x_data is None or self.y_data is None or len(self.x_data) < 4:
        return None

    def gaussian(x, amplitude, center, width):
        return amplitude * np.exp(-(x - center)**2 / (2 * width**2))

    def lorentzian(x, amplitude, center, width):
        return amplitude / (1 + ((x - center) / width)**2)

    def sech_squared(x, amplitude, center, width):
        return amplitude / np.cosh((x - center) / width)**2

    if fit_type == FIT_GAUSS:
      fit_func = gaussian
      fit_label = "Gaussian Fit"
    elif fit_type == FIT_LORENTZ:
      fit_func = lorentzian
      fit_label = "Lorentzian Fit"
    elif fit_type == FIT_SECH2:
      fit_func = sech_squared
      fit_label = "sech² Fit"
    else:
        return None

    try:
      amplitude_guess = np.max(self.y_data)
      center_guess = np.mean(self.x_data)
      width_guess = (np.max(self.x_data) - np.min(self.x_data)) / 6
      popt, pcov = curve_fit(fit_func, self.x_data, self.y_data,
                            p0=[amplitude_guess, center_guess, width_guess],
                            maxfev=10000)

      x_fit = np.linspace(self.x_data[0], self.x_data[-1], num_points)
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

  def show_fit_params(self, fit_params):
    # TODO: calculate experimental (measured) profile FWHM
    # TODO: calculate pulse duration from autocorrelation profile
    # TODO: output as text on the plot in left-top corner:
    # TODO:   - Pulse duration (estimated)
    # TODO:   - Fit profile FWHM
    # TODO:   - Measured profile FWHM
    # TODO:   - Profile center
    # TODO:   - Profile amplitude
    pass
