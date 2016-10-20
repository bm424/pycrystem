from unittest import TestCase
from unittest.mock import MagicMock as Mock
from unittest.mock import patch

import numpy as np
from pycrystem.diffraction_generator import ElectronDiffractionCalculator


class TestElectronDiffractionCalculator(TestCase):

    def setUp(self):
        self.calculator = ElectronDiffractionCalculator(300., 4., 5e-2)
        self.structure = Mock()
        self.indices = np.array([
            [0., 0., 0.],
            [0., 1., 0.],
            [0., 1., 20.]
        ])
        self.proximities = np.array([0., 0.019, 20.])

    def test_calculate_ed_data_points_call(self):
        reciprocal_lattice = self.structure.lattice\
            .reciprocal_lattice_crystallographic
        reciprocal_lattice.get_points_in_sphere.return_value = self.indices
        reciprocal_lattice.get_cartesian_coordinates.return_value =
        self.calculator.calculate_ed_data(self.structure)
        reciprocal_lattice.get_points_in_sphere.assert_called_with(
            [[0, 0, 0]],
            [0, 0, 0],
            self.calculator.reciprocal_radius
        )

    def test_ewald_intersection(self):
        intersection, p = self.calculator.ewald_intersection(self.indices)
        np.testing.assert_array_equal(intersection, [1, 1, 0])

    @patch('pycrystem.diffraction_generator.get_structure_factors')
    def test_get_peak_intensities_sf_call(self, get_structure_factors_patch):
        self.calculator.get_peak_intensities(self.structure, self.indices,
                                             self.proximities)
        get_structure_factors_patch.assert_called_with(self.indices,
                                                       self.structure)

    @patch('pycrystem.diffraction_generator.get_structure_factors')
    def test_get_peak_intensities_correct_answer(self,
                                                 get_structure_factors_patch):
        get_structure_factors_patch.return_value = np.array([36, 36])
        intensities = self.calculator.get_peak_intensities(self.structure,
                                                           self.indices[:2],
                                                           self.proximities[:2])
        np.testing.assert_array_almost_equal(intensities, [6, 4.7244],
                                             decimal=4)

