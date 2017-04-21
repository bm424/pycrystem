import numpy as np
from IPython.core.display import clear_output, display
from ipywidgets import Button, FloatSlider, Text
from matplotlib import pyplot as plt
from pymatgen.transformations.standard_transformations import \
    RotationTransformation
from transforms3d.euler import euler2axangle

from pycrystem.utils import correlate
from pycrystem.indexation_generator import IndexationGenerator
from pycrystem.diffraction_signal import ElectronDiffraction


class ManualOrientation:

    def __init__(
        self,
        data,  #: ElectronDiffraction
        structure,  #: Structure
        calculator,  #: ElectronDiffractionCalculator
        library=None,  #: DiffractionLibrary
        ax=None,
    ):

        self.data = data
        self.structure = structure
        self.calculator = calculator
        self.library = library
        self.plot, self.scatter = self.create_plot(ax)
        self.widgets = self.create_widgets()

        for widget in self.widgets:
            display(widget)

        self.update()

    def create_plot(self, ax):

        if ax is None:
            ax = plt.figure().add_subplot(111)
        dimension = self.data.axes_manager.signal_shape[0] / 2
        extent = [-dimension, dimension] * 2
        data = self.data.inav[self.data.axes_manager.coordinates]
        ax.imshow(data.data, extent=extent, interpolation='none', origin='lower')
        scatter = ax.scatter([0, ], [0, ], s=0)
        ax.set_xlim(-dimension, dimension)
        ax.set_ylim(-dimension, dimension)
        plt.show()
        return ax, scatter

    def create_widgets(self):

        auto_solve_button = Button(description="Solve",
                                   disabled=self.library is None,
                                   icon="dot-circle-o")

        correlation_text = Text(value="", description="Correlation: ",
                                disabled=True)

        alpha_slider = FloatSlider(0.0, min=-np.pi, max=np.pi, step=0.01,
                                   description='Alpha:', readout_format='.2f',
                                   width='75%')
        beta_slider = FloatSlider(0.0, min=0., max=np.pi / 4., step=0.01,
                                  description='Beta:', readout_format='.2f',
                                  width='75%')
        gamma_slider = FloatSlider(0.0, min=-np.pi / 4., max=np.pi / 4.,
                                   step=0.01, description='Gamma:',
                                   readout_format='.2f', width='75%')
        calibration_slider = FloatSlider(1e-2, min=0., max=2e-2, step=1e-4,
                                         description=u'Calibration {}/px:'.format(
                                             u'\u212b\u207b\u00b9'.format(
                                                 'utf-8')),
                                         readout_format='.4f', width='75%')

        optimise_calibration_button = Button(description="Optimise calibration")

        # sliders = [alpha_slider, beta_slider, gamma_slider, calibration_slider]
        # for slider in sliders:
        #     display(slider)
        #     slider.observe(on_change, names='value')

        return [
            auto_solve_button,
            correlation_text,
            alpha_slider,
            beta_slider,
            gamma_slider,
            calibration_slider,
            optimise_calibration_button,
        ]

    def update(self, alpha=0., beta=0., gamma=0., calibration=0.01, reciprocal_radius=1.5):
        orientation = euler2axangle(alpha, beta, gamma, 'rzyz')
        rotation = RotationTransformation(orientation[0], orientation[1],
                                          angle_in_radians=True).apply_transformation(
            self.structure)
        electron_diffraction = self.calculator.calculate_ed_data(rotation, reciprocal_radius)
        electron_diffraction.calibration = calibration
        self.scatter.remove()
        self.scatter = plt.scatter(
            electron_diffraction.calibrated_coordinates[:, 0],
            electron_diffraction.calibrated_coordinates[:, 1],
            s=np.sqrt(electron_diffraction.intensities),
            facecolors='none',
            edgecolors='r'
        )
        # correlation_text.value = str(correlate(data.data, electron_diffraction))
        plt.show()

    def solve(self, button):
        # self.library.set_calibration(calibration_slider.value)
        indexer = IndexationGenerator(self.data, self.library)
        correlation = indexer.correlate(show_progressbar=False)[0]
        key = list(correlation.keys())[0]
        return correlation[key].best

    # def auto_solve(button):
    #     (alpha_slider.value, beta_slider.value, gamma_slider.value) = solve()[0]

    # def calibrate(button):
    #     calibration_best = 0.
    #     for calibration in np.arange(0., 2., 0.01):
    #         calibration_slider.value = calibration
    #
    #
    # def on_change(change):
    #     clear_output(wait=True)
    #     update(alpha_slider.value, beta_slider.value, gamma_slider.value, calibration_slider.value)
