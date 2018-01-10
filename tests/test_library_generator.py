# -*- coding: utf-8 -*-
# Copyright 2018 The pyXem developers
#
# This file is part of pyXem.
#
# pyXem is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyXem is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyXem.  If not, see <http://www.gnu.org/licenses/>.

import pytest
import numpy as np
from math import pi
import pymatgen as pmg

from pyxem.diffraction_generator import ElectronDiffractionCalculator
from pyxem.library_generator import DiffractionLibraryGenerator, DiffractionLibrary
from hyperspy.signals import Signal1D, Signal2D

@pytest.fixture(params=[
    np.array([
        [pi/4, pi/3, pi],
        [pi/9, -pi/4, 3*pi/4],
    ])
])
def orientations(request):
    return np.array(request.param)


@pytest.fixture
def structure_library():
    lattice1 = pmg.Lattice.cubic(5.431)
    lattice2 = pmg.Lattice.hexagonal(1.531, 5)
    structure1 = pmg.Structure.from_spacegroup("Fd-3m", lattice1, ["Si"], [[0, 0, 0]])
    structure2 = pmg.Structure.from_spacegroup("P6_3mc", lattice2, ["Ga"], [[0, 0, 0]])
    orientations1 = np.array([
        [pi / 4, pi / 3, pi],
        [pi / 9, -pi / 4, 3 * pi / 4],
    ])
    orientations2 = np.array([
        [0, 0, 0],
        [0, pi/2, 0],
        [pi/4, pi/2, pi/4],
    ])
    return {
        'phase 1': (structure1, orientations1),
        'phase 2': (structure2, orientations2)
    }


@pytest.fixture
def diffraction_calculator():
    return ElectronDiffractionCalculator(300., 0.02)


@pytest.fixture
def library_generator(diffraction_calculator):
    return DiffractionLibraryGenerator(diffraction_calculator)


@pytest.fixture
def calculated_library(library_generator, structure_library):
    return library_generator.get_diffraction_library(structure_library, 0.02, 3., 'euler')


class TestDiffractionLibraryGenerator:

    def test_library_type(self, calculated_library):
        assert isinstance(calculated_library, DiffractionLibrary)

    def test_library_phases(self, calculated_library, structure_library):
        assert list(calculated_library.keys()) == list(structure_library.keys())

    def test_library_orientations(self, calculated_library, structure_library):
        for phase in calculated_library:
            assert list(calculated_library[phase].keys()) == list(map(tuple, structure_library[phase][1]))


class TestDiffractionLibrary:

    @pytest.mark.parametrize('calibration', [
        0.5, 0.7, (0.25, 0.1),
    ])
    def test_set_calibration(self, calculated_library: DiffractionLibrary, calibration):
        calculated_library.set_calibration(calibration)
        for phase in calculated_library:
            for orientation in calculated_library[phase]:
                pattern = calculated_library[phase][orientation]
                assert np.all(np.equal(pattern.calibration, calibration))

    @pytest.mark.parametrize('offset', [
        (1, 1), pytest.param(1, marks=pytest.mark.xfail)
    ])
    def test_set_offset(selfself, calculated_library: DiffractionLibrary, offset):
        calculated_library.set_offset(offset)
        for phase in calculated_library:
            for orientation in calculated_library[phase]:
                pattern = calculated_library[phase][orientation]
                assert np.all(np.equal(pattern.offset, offset))
