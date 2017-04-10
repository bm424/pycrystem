import numpy as np
from IPython.core.display import clear_output, display
from ipywidgets import Button, FloatSlider
from matplotlib import pyplot as plt
from pymatgen.transformations.standard_transformations import \
    RotationTransformation
from transforms3d.euler import euler2axangle

from pycrystem.indexation_generator import IndexationGenerator


def manual_orientation(
        data,  #: np.ndarray,
        structure,  #: Structure,
        calculator,  #: ElectronDiffractionCalculator,
        library = None, #: DiffractionLibrary
        ax=None,
):
    if ax is None:
        ax = plt.figure().add_subplot(111)
    dimension = data.axes_manager.signal_shape[0] / 2
    extent = [-dimension, dimension] * 2
    ax.imshow(data.data, extent=extent, interpolation='none', origin='lower')
    p = ax.scatter([0, ], [0, ], s=0)
    plt.show()

    def update(alpha=0., beta=0., gamma=0., calibration=1.):
        orientation = euler2axangle(alpha, beta, gamma, 'rzyz')
        rotation = RotationTransformation(orientation[0], orientation[1],
                                          angle_in_radians=True).apply_transformation(
            structure)
        electron_diffraction = calculator.calculate_ed_data(rotation, library.reciprocal_radius)
        electron_diffraction.calibration = calibration
        nonlocal p
        p.remove()
        p = plt.scatter(
            electron_diffraction.calibrated_coordinates[:, 0],
            electron_diffraction.calibrated_coordinates[:, 1],
            s=np.sqrt(electron_diffraction.intensities),
            facecolors='none',
            edgecolors='r'
        )
        ax.set_xlim(-dimension, dimension)
        ax.set_ylim(-dimension, dimension)
        plt.show()

    def solve(button):
        library.set_calibration(calibration_slider.value)
        indexer = IndexationGenerator(data, library)
        correlation = indexer.correlate(show_progressbar=False)[0]
        key = list(correlation.keys())[0]
        print(correlation[key].best[0])
        (alpha_slider.value, beta_slider.value, gamma_slider.value) = correlation[key].best[0]

    def on_change(change):
        clear_output(wait=True)
        update(alpha_slider.value, beta_slider.value, gamma_slider.value, calibration_slider.value/100.)

    auto_solve_button = Button(value=False, description="Solve", disabled=library is None)
    auto_solve_button.on_click(solve)

    alpha_slider = FloatSlider(0.0, min=-np.pi, max=np.pi, step=0.01, description='Alpha:', readout_format='.2f', width='75%')
    beta_slider = FloatSlider(0.0, min=0., max=np.pi/4., step=0.01, description='Beta:', readout_format='.2f', width='75%')
    gamma_slider = FloatSlider(0.0, min=-np.pi/4., max=np.pi/4., step=0.01, description='Gamma:', readout_format='.2f', width='75%')
    calibration_slider = FloatSlider(1.0, min=0., max=2., step=0.01, description=u'Calibration {}/px:'.format(u'\u212b\u207b\u00b9'.format('utf-8')), readout_format='.2f', width='75%')

    display(auto_solve_button)
    sliders = [alpha_slider, beta_slider, gamma_slider, calibration_slider]

    for slider in sliders:
        display(slider)
        slider.observe(on_change, names='value')