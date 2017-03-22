# -*- coding: utf-8 -*-
# Copyright 2016 The PyCrystEM developers
#
# This file is part of PyCrystEM.
#
# PyCrystEM is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PyCrystEM is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PyCrystEM.  If not, see <http://www.gnu.org/licenses/>.
"""Kinematical diffraction pattern calculation.

"""


from __future__ import division

import numpy as np
from hyperspy.components2d import Gaussian2D

from pycrystem.diffraction_signal import ElectronDiffraction
from pycrystem.utils.simulation import get_electron_wavelength,\
    get_kinematical_intensities
from pymatgen.util.plotting_utils import get_publication_quality_plot


class ElectronDiffractionGenerator(object):
    """Computes electron diffraction patterns for a crystal structure.

    1. Calculate reciprocal lattice of structure. Find all reciprocal points
       within the limiting sphere given by :math:`\\frac{2}{\\lambda}`.

    2. For each reciprocal point :math:`\\mathbf{g_{hkl}}` corresponding to
       lattice plane :math:`(hkl)`, compute the Bragg condition
       :math:`\\sin(\\theta) = \\frac{\\lambda}{2d_{hkl}}`

    3. The intensity of each reflection is then given in the kinematic
       approximation as the modulus square of the structure factor.
       .. math::
          I_{hkl} = F_{hkl}F_{hkl}^*


    Parameters
    ----------
    accelerating_voltage : float
        The accelerating voltage of the microscope in kV
    max_excitation_error : float
        The maximum extent of the relrods in reciprocal angstroms. Typically
        equal to 1/{specimen thickness}.


    .. todo::
        Include camera length, when implemented.

    .. todo::
        Refactor the excitation error to a structure property.

    """

    def __init__(self,
                 accelerating_voltage,
                 max_excitation_error,
                 debye_waller_factors=None):
        self.wavelength = get_electron_wavelength(accelerating_voltage)
        self.max_excitation_error = max_excitation_error
        self.debye_waller_factors = debye_waller_factors or {}

    def calculate_ed_data(self,
                          structure,
                          reciprocal_radius):
        """Calculates the Electron Diffraction data for a structure.

        Parameters
        ----------
        structure : Structure
            The structure for which to derive the diffraction pattern. Note
            that the structure must be rotated to the appropriate orientation.
        reciprocal_radius : float
            The radius of reciprocal space from which to sample the reciprocal
            lattice, in Angstroms.

        Returns
        -------
        :class:`DiffractionSimulation`
            The data associated with this structure and diffraction setup.

        """
        # Specify variables used in calculation
        max_excitation_error = self.max_excitation_error
        debye_waller_factors = self.debye_waller_factors
        lattice = structure.lattice

        reciprocal_points, g_hkls, cartesian_coordinates = \
            self.sample_reciprocal_lattice(lattice, reciprocal_radius)

        g_hkls, intersection_coordinates, intersection_indices, proximity = \
            self.ewald_sphere_intersection(reciprocal_points,
                                           g_hkls,
                                           cartesian_coordinates)
        # Calculate diffracted intensities based on a kinematical model.
        intensities = get_kinematical_intensities(structure,
                                                  intersection_indices,
                                                  g_hkls,
                                                  proximity,
                                                  max_excitation_error,
                                                  debye_waller_factors)

        # Threshold peaks included in simulation based on minimum intensity.
        peak_mask = intensities > 1e-20
        intensities = intensities[peak_mask]
        intersection_coordinates = intersection_coordinates[peak_mask]
        intersection_indices = intersection_indices[peak_mask]

        return DiffractionSimulation(coordinates=intersection_coordinates,
                                     indices=intersection_indices,
                                     intensities=intensities)

    def ewald_sphere_intersection(self, reciprocal_points, g_hkls,
                                  cartesian_coordinates):
        """Determine lattice points intersecting the Ewald sphere.

        Parameters
        ----------
        reciprocal_points : :class:`numpy.ndarray`
            The miller indices of the sampled reciprocal space points.
        g_hkls : :class:`numpy.ndarray`
            ???
        cartesian_coordinates : :class:`numpy.ndarray`
            The reciprocal space coordinates of the sampled points.

        Returns
        -------
        g_hkls : :class:`numpy.ndarray`
            ???
        intersection_coordinates : :class:`numpy.ndarray`
            The reciprocal space coordinates of the points that intersect the
            Ewald sphere.
        intersection_indices : :class:`numpy.ndarray`
            The Miller indices of the points that intersect the Ewald sphere.
        proximity : :class:`numpy.ndarray`
            The vertical (z) distances between points that intersect the Ewald
            sphere and the sphere itself.

        """
        # Identify points intersecting the Ewald sphere within maximum
        # excitation error and store the magnitude of their excitation error.
        radius = 1. / self.wavelength
        r = np.sqrt(np.sum(np.square(cartesian_coordinates[:, :2]), axis=1))
        theta = np.arcsin(r / radius)
        z_sphere = radius * (1 - np.cos(theta))
        proximity = np.absolute(z_sphere - cartesian_coordinates[:, 2])
        intersection = proximity < self.max_excitation_error
        # Mask parameters corresponding to excited reflections.
        intersection_coordinates = cartesian_coordinates[intersection]
        intersection_indices = reciprocal_points[intersection]
        proximity = proximity[intersection]
        g_hkls = g_hkls[intersection]
        return (g_hkls, intersection_coordinates, intersection_indices,
                proximity)

    def sample_reciprocal_lattice(self, lattice, reciprocal_radius):
        """Crystallographic reciprocal lattice points g-vector magnitudes.

        Parameters
        ----------
        lattice : :class:`pymatgen.core.lattice.Lattice`
            The *real* crystallographic lattice.
        reciprocal_radius : float
            The radius of reciprocal space from which to sample the reciprocal
            lattice, in Angstroms.

        Returns
        -------
        reciprocal_points : :class:`numpy.ndarray`
            The miller indices of the sampled reciprocal space points.
        g_hkls : :class:`numpy.ndarray`
            ???
        cartesian_coordinates : :class:`numpy.ndarray`
            The reciprocal space coordinates of the sampled points.

        """
        reciprocal_lattice = lattice.reciprocal_lattice_crystallographic
        reciprocal_points = \
            reciprocal_lattice.get_points_in_sphere([[0, 0, 0]],
                                                    [0, 0, 0],
                                                    reciprocal_radius,
                                                    zip_results=False)[0]
        g_hkls = \
            reciprocal_lattice.get_points_in_sphere([[0, 0, 0]],
                                                    [0, 0, 0],
                                                    reciprocal_radius,
                                                    zip_results=False)[1]
        cartesian_coordinates = \
            reciprocal_lattice.get_cartesian_coords(reciprocal_points)
        return reciprocal_points, g_hkls, cartesian_coordinates


class DiffractionSimulation:

    def __init__(self, coordinates=None, indices=None, intensities=None,
                 calibration=1., offset=(0., 0.), with_direct_beam=False):
        """Holds the result of a given diffraction pattern.

        Parameters
        ----------
        coordinates : array-like
            The x-y coordinates of points in reciprocal space.
        indices : array-like
            The indices of the reciprocal lattice points that intersect the
            Ewald sphere.
        intensities : array-like
            The intensities of each diffraction spot.
        calibration : {:obj:`float`, :obj:`tuple` of :obj:`float`}, optional
            The x- and y-scales of the pattern, with respect to the original
            reciprocal angstrom coordinates.
        offset : :obj:`tuple` of :obj:`float`, optional
            The x-y offset of the pattern in reciprocal angstroms. Defaults to
            zero in each direction.
        """
        self._coordinates = None
        self.coordinates = coordinates
        self.indices = indices
        self._intensities = None
        self.intensities = intensities
        self._calibration = (1., 1.)
        self.calibration = calibration
        self.offset = offset
        self.with_direct_beam = with_direct_beam

    @property
    def calibrated_coordinates(self):
        """Coordinates converted into pixel space."""
        coordinates = np.copy(self.coordinates)
        coordinates[:, 0] += self.offset[0]
        coordinates[:, 1] += self.offset[1]
        coordinates[:, 0] /= self.calibration[0]
        coordinates[:, 1] /= self.calibration[1]
        return coordinates.astype(int)

    @property
    def calibration(self):
        return self._calibration

    @calibration.setter
    def calibration(self, calibration):
        if isinstance(calibration, float) or isinstance(calibration, int):
            self._calibration = (calibration, calibration)
        elif len(calibration) == 2:
            self._calibration = calibration
        else:
            raise ValueError("`calibration` must be a float, int, or length-2"
                             "tuple of floats or ints.")

    @property
    def direct_beam_mask(self):
        if self.with_direct_beam:
            return np.ones_like(self._intensities, dtype=bool)
        else:
            return np.sum(self._coordinates == 0., axis=1) != 3

    @property
    def coordinates(self):
        return self._coordinates[self.direct_beam_mask]

    @coordinates.setter
    def coordinates(self, coordinates):
        self._coordinates = coordinates

    @property
    def intensities(self):
        return self._intensities[self.direct_beam_mask]

    @intensities.setter
    def intensities(self, intensities):
        self._intensities = intensities

    def plot(self, ax=None):
        """Returns the diffraction data as a plot.

        Parameters
        ----------
        ax : :class:`matplotlib.axes.Axes`, optional
            If supplied, the figure will be drawn on the specified axes. If
            not, the current active axis will be used.

        Notes
        -----
        Run `.show()` on the result of this method to display the plot.

        """
        if ax is None:
            plt = get_publication_quality_plot(10, 10)
            ax = plt.gca()
        ax.scatter(
            self.coordinates[:, 0],
            self.coordinates[:, 1],
            s=np.log10(self.intensities)
        )
        ax.set_xlabel("Reciprocal Dimension ($A^{-1}$)")
        ax.set_ylabel("Reciprocal Dimension ($A^{-1}$)")
        return ax

    def as_signal(self, size, sigma, max_r):
        """Returns the diffraction data as an ElectronDiffraction signal

        Gaussian functions are used to represent each diffracted peak.

        Parameters
        ----------
        size : int
            (x, y) signal_shape for the signal to be simulated.
        sigma : float
            Standard deviation of the Gaussian function to be plotted.
        max_r : float
            Boundaries of the signal in reciprocal Angstroms.

        """
        # Plot a 2D Gaussian at each peak position.
        # TODO: Update this method so plots intensity at each position and then
        # convolves with a Gaussian to make faster - needs interpolation care.
        dp_dat = np.zeros(size)
        l = np.linspace(-max_r, max_r, size)
        x, y = np.meshgrid(l, l)
        i = 0
        while i < len(self.intensities):
            cx = self.coordinates[i][0]
            cy = self.coordinates[i][1]
            inten = self.intensities[i]
            g = Gaussian2D(A=inten,
                           sigma_x=sigma,
                           sigma_y=sigma,
                           centre_x=cx,
                           centre_y=cy)
            dp_dat = dp_dat + g.function(x, y)
            i += 1

        dp = ElectronDiffraction(dp_dat)
        dp.set_calibration(max_r / size)

        return dp
