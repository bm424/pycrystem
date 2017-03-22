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
"""Diffraction pattern library generator and associated tools.

"""

from __future__ import division
from math import radians

import numpy as np
from hyperspy.signals import BaseSignal
from pymatgen.transformations.standard_transformations \
    import RotationTransformation
from scipy.interpolate import griddata
from tqdm import tqdm
from transforms3d.euler import euler2axangle
from scipy.constants import pi


class DiffractionLibraryGenerator(object):
    """
    Computes a series of electron diffraction patterns using a kinematical model
    """

    def __init__(self, electron_diffraction_calculator):
        """Initialises the library with a diffraction calculator.

        Parameters
        ----------
        electron_diffraction_calculator : :class:`ElectronDiffractionCalculator`
            The calculator used for the diffraction patterns.

        """
        self.electron_diffraction_calculator = electron_diffraction_calculator

    def get_diffraction_library(self,
                                structure_library,
                                calibration,
                                reciprocal_radius,
                                representation='euler'):
        """Calculates a list of diffraction data for a library of crystal
        structures and orientations.

        Each structure in the structure library is rotated to each associated
        orientation and the diffraction pattern is calculated each time.

        Parameters
        ----------
        structure_library : dict
            Maps structure names to a tuple of a structure and an orientation.
        calibration : float
            The calibration of experimental data to be correlated with the
            library, in reciprocal Angstroms per pixel.
        reciprocal_radius : float
            The maximum g-vector magnitude to be accepted.
        representation : 'euler' or 'axis-angle'
            The representation in which the orientations are provided.
            If 'euler' the zxz convention is taken and values are in radians, if
            'axis-angle' the rotational angle is in degrees.

        Returns
        -------
        diffraction_library : dict of :class:`DiffractionSimulation`
            Mapping of crystal structure and orientation to diffraction data
            objects.

        """
        # Define DiffractionLibrary object to contain results
        diffraction_library = DiffractionLibrary()
        # The electron diffraction calculator to do simulations
        diffractor = self.electron_diffraction_calculator
        # Iterate through phases in library.
        for structure_key in structure_library.keys():
            phase_diffraction_library = dict()
            structure = structure_library[structure_key][0]
            orientations = structure_library[structure_key][1]
            # Iterate through orientations of each phase.

            orientations = self.parse_axis_angle(orientations, representation)

            for orientation in tqdm(orientations, leave=False):
                axis = [orientation[0], orientation[1], orientation[2]]
                angle = radians(orientation[3])

                # Apply rotation to the structure
                rotation = RotationTransformation(axis, angle,
                                                  angle_in_radians=True)
                structure_rotated = rotation.apply_transformation(structure)
                # Calculate electron diffraction for rotated structure
                simulation = diffractor.calculate_ed_data(structure_rotated,
                                                          reciprocal_radius)
                # Calibrate simulation
                simulation.calibration = calibration
                # Construct diffraction simulation library.
                phase_diffraction_library[tuple(orientation)] = simulation
            diffraction_library[structure_key] = phase_diffraction_library
        return diffraction_library

    def parse_axis_angle(self, orientations, representation):
        orientations_axangle = np.zeros((len(orientations), 4))
        if representation is 'euler':
            for o_1, o_2 in zip(orientations, orientations_axangle):
                o_2[:3], o_2[3] = euler2axangle(*o_1, 'rzxz')
        elif representation is 'axis-angle':
            orientations_axangle = orientations
        else:
            raise ValueError("`representation` must be "
                             "'euler' or 'axis-angle'")
        return orientations_axangle


class DiffractionLibrary(dict):
    """Maps crystal structure (phase) and orientation (Euler angles or
    axis-angle pair) to simulated diffraction data.
    """

    @property
    def structures(self):
        return self.keys()

    @property
    def libraries(self):
        return self.values()

    def set_calibration(self, calibration):
        """Sets the scale of every diffraction pattern simulation in the
        library.

        Parameters
        ----------
        calibration : {:obj:`float`, :obj:`tuple` of :obj:`float`}, optional
            The x- and y-scales of the patterns, with respect to the original
            reciprocal angstrom coordinates.

        """
        for structure_library in self.libraries:
            for diffraction_pattern in structure_library.values():
                diffraction_pattern.calibration = calibration

    def set_offset(self, offset):
        """Sets the offset of every diffraction pattern simulation in the
        library.

        Parameters
        ----------
        offset : :obj:`tuple` of :obj:`float`, optional
            The x-y offset of the patterns in reciprocal angstroms. Defaults to
            zero in each direction.

        """
        assert len(offset) == 2
        for structure_library in self.libraries:
            for diffraction_pattern in structure_library.values():
                diffraction_pattern.offset = offset

    def plot(self):
        """Plots the library interactively.
        """
        from pycrystem.diffraction_signal import ElectronDiffraction
        sim_diff_dat = []
        for key in self.keys():
            for ori in self[key].keys():
                dpi = self[key][ori].as_signal(128, 0.03, 1)
                sim_diff_dat.append(dpi.data)
        ppt_test = ElectronDiffraction(sim_diff_dat)
        ppt_test.plot()
