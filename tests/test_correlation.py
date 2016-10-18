from unittest import TestCase

from pycrystem.utils.correlation import *


class TestNormalizedCorrelation(TestCase):

    def setUp(self):

        self.intensities_1 = [1, 0, 1, 0, 1]
        self.intensities_2 = [0, 1, 0, 1, 0]

    def test_perfect_correlation(self):
        correlation = normalized_correlation(self.intensities_1,
                                             self.intensities_1)
        self.assertAlmostEqual(correlation, 1)

    def test_inverse_correlation(self):
        correlation = normalized_correlation(self.intensities_1,
                                             self.intensities_2)
        self.assertAlmostEqual(correlation, 0)
