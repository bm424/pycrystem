import numpy as np

from pycrystem.utils import get_point_intensities


def correlate(image, pattern, method='default'):
    """The correlation between a diffraction pattern and a simulation.

    Parameters
    ----------
    image : :class:`ElectronDiffraction`
        A single electron diffraction signal. Should be appropriately scaled
        and centered.
    pattern : :class:`DiffractionSimulation`
        The pattern to compare to.
    method : {'default'}
        The correlation method to use.

    .. todo::
        Implement system for choosing alternative correlation methods.

    Returns
    -------
    float
        The correlation coefficient.

    """
    methods = {
        'default': normalized_correlation,
    }
    method = methods[method]
    return method(*get_point_intensities(image, pattern))


def normalized_correlation(intensities_1, intensities_2):
    """The normalized correlation between two sets of intensities.

    Adapted from [1]_.

    Calculated using
        .. math::
            \frac{\sum_{j=1}^m P(x_j, y_j) T(x_j, y_j)}{\sqrt{\sum_{j=1}^m P^2(x_j, y_j)} \sqrt{\sum_{j=1}^m T^2(x_j, y_j)}}

    Parameters
    ----------
    intensities_1, intensities_2 : array-like
        Intensities to compare.

    References
    ----------
    .. [1] E. F. Rauch and L. Dupuy, “Rapid Diffraction Patterns
       identification through template matching,” vol. 50, no. 1, pp. 87–99,
       2005.

    """

    return np.dot(intensities_1, intensities_2) / (
        np.sqrt(np.dot(intensities_1, intensities_1)) *
        np.sqrt(np.dot(intensities_2, intensities_2))
    )