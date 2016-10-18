# -*- coding: utf-8 -*-

import numpy as np


def get_point_intensities(image, pattern):
    """Fetches image intensities where the pattern and image overlap.

    Parameters
    ----------
    image : :class:`ElectronDiffraction`
        A single electron diffraction signal. Should be appropriately scaled
        and centered.
    pattern : :class:`DiffractionSimulation`
        The pattern to compare to.

    Returns
    -------
    image_intensities : ndarray
        The intensities of the image where there are spots in the pattern.
    pattern_intensities : ndarray
        The intensities of the pattern where it overlaps the image.

    """

    signal_shape = image.axes_manager.signal_shape
    x, y = pattern.to_pixels(signal_shape)
    condition = get_boundary_constraints(x, y, *signal_shape)
    x = x[condition]
    y = y[condition]
    image_intensities = image.get_point_intensities(x, y)
    pattern_intensities = pattern.intensities[condition]
    return image_intensities, pattern_intensities


def get_boundary_constraints(x, y, x_max, y_max):
    """Returns True where x and y are within 0 and their respective maxes."""
    x_bounds = np.logical_and(0 <= x, x < x_max)
    y_bounds = np.logical_and(0 <= y, y < y_max)
    condition = np.logical_and(x_bounds, y_bounds)
    return condition
