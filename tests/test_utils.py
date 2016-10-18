from unittest import TestCase
from unittest.mock import MagicMock as Mock

import numpy as np
from pycrystem.utils import *


class TestGetPointIntensities(TestCase):

    def setUp(self):
        image = Mock()
        image.axes_manager.signal_shape = (10, 10)
        pattern = Mock()
        pattern.to_pixels.return_value = (np.array([4, 8, 12]),
                                          np.array([-1, 7, 13]))
        pattern.intensities = np.array([0, 1, 2])
        self.image = image
        self.pattern = pattern

    def test_call_to_pixels(self):
        get_point_intensities(self.image, self.pattern)
        self.pattern.to_pixels.assert_called_with(
            self.image.axes_manager.signal_shape)

    def test_call_to_image_get_point_intensities(self):
        get_point_intensities(self.image, self.pattern)
        self.image.get_point_intensities.assert_called_with(
            np.array([8,]), np.array([7,])
        )

    def test_correct_pattern_intensities(self):
        i, p = get_point_intensities(self.image, self.pattern)
        self.assertEqual(p, 1)


class TestGetBoundaryConstraints(TestCase):

    def setUp(self):
        self.x = np.array([4, 8, 10])
        self.y = np.array([-1, 7, 13])
        self.x_max = 10
        self.y_max = 10

    def test_get_boundary_constraints(self):
        condition = get_boundary_constraints(self.x, self.y, self.x_max,
                                             self.y_max)
        np.testing.assert_array_equal(condition, [0, 1, 0])



