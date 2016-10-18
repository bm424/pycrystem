from unittest import TestCase
from unittest.mock import MagicMock as Mock

import numpy as np
from pycrystem.diffraction_generator import ElectronDiffractionCalculator


class TestElectronDiffractionCalculator(TestCase):

    def setUp(self):
        self.calculator = ElectronDiffractionCalculator(300., 4., 1e-2)
        self.structure = Mock()

    def test_calculate_ed_data(self):
        pass

    def test_ewald_intersection(self):
        coordinates = np.array([
            [0., 0., 0.],
            [0., 1., 0.],
            [0., 1., 20.]
        ])
        intersection, p = self.calculator.ewald_intersection(coordinates)
        np.testing.assert_array_equal(intersection, [1, 1, 0])

    def test_get_peak_intensities(self):
        pass
