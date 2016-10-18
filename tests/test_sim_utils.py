from unittest import TestCase
from unittest.mock import MagicMock as Mock

import numpy as np
from pycrystem.utils.sim_utils import get_electron_wavelength,\
    get_structure_factors


class TestGetElectronWavelength(TestCase):

    def test_get_electron_wavelength(self):

        wavelength = get_electron_wavelength(300)
        self.assertAlmostEqual(wavelength, 0.019687, 5)


class TestGetStructureFactors(TestCase):

    def setUp(self):
        atoms = [Mock(), Mock(), Mock()]
        for atom in atoms:
            atom.number = 2
        structure = Mock()
        structure.species = atoms
        structure.frac_coords = np.array([
            [1, 0, 0],
            [0, -1, 0],
            [0, 0, 1]
        ])
        self.fractional_coordinates = np.array([
            [1, 0, 0],
            [1, 1, 0]
        ])
        self.structure = structure

    def test_get_structure_factors(self):
        structure_factors = get_structure_factors(
            self.fractional_coordinates, self.structure)
        np.testing.assert_array_equal(structure_factors, [36, 36])
