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
from __future__ import division
import pkg_resources

import itertools
import math
from decimal import Decimal, ROUND_HALF_UP
from math import radians, sin

import numpy as np
from scipy.constants import h, m_e, e, c, pi
import json

ASP_FILE = pkg_resources.resource_filename(
    'pycrystem', 'data/atomic_scattering_params.json'
)

with open(ASP_FILE) as f:
    ATOMIC_SCATTERING_PARAMS = json.load(f)


def get_electron_wavelength(accelerating_voltage):
    """Calculates the (relativistic) electron wavelength in Angstroms
    for a given accelerating voltage in kV.

    Evaluates

    Parameters
    ----------
    accelerating_voltage : float
        The accelerating voltage in kV.

    Returns
    -------
    wavelength : float
        The relativistic electron wavelength in Angstroms.

    """
    E = accelerating_voltage*1e3
    wavelength = h / math.sqrt(2 * m_e * e * E *
                               (1 + (e / (2 * m_e * c * c)) * E)) * 1e10
    return wavelength


def get_interaction_constant(accelerating_voltage):
    """Calculates the interaction constant, sigma, for a given
    acelerating voltage.

    Evaluates

    Parameters
    ----------
    accelerating_voltage : float
        The accelerating voltage in V.

    Returns
    -------
    sigma : float
        The relativistic electron wavelength in m.

    """
    E = accelerating_voltage
    wavelength = get_electron_wavelength(accelerating_voltage)
    sigma = (2 * pi * (m_e + e * E))

    return sigma


def get_kinematical_intensities(structure,
                                g_indices,
                                g_hkls,
                                excitation_error,
                                maximum_excitation_error,
                                debye_waller_factors):
    """Calculates peak intensities.

    The peak intensity is a combination of the structure factor for a given
    peak and the position the Ewald sphere intersects the relrod. In this
    implementation, the intensity scales linearly with proximity.

    Parameters
    ----------
    structure : Structure
        The structure for which to derive the structure factors.
    indices : array-like
        The fractional coordinates of the peaks for which to calculate the
        structure factor.
    proximities : array-like
        The distances between the Ewald sphere and the peak centres.

    Returns
    -------
    peak_intensities : array-like
        The intensities of the peaks.

    """
    # Create a flattened array of zs, coeffs, fcoords and occus for vectorized
    # computation of atomic scattering factors later. Note that these are not
    # necessarily the same size as the structure as each partially occupied
    # specie occupies its own position in the flattened array.
    zs = []
    coeffs = []
    fcoords = []
    occus = []
    dwfactors = []
    for site in structure:
        for sp, occu in site.species_and_occu.items():
            zs.append(sp.Z)
            try:
                c = ATOMIC_SCATTERING_PARAMS[sp.symbol]
            except KeyError:
                raise ValueError("Unable to calculate XRD pattern as "
                                 "there is no scattering coefficients for"
                                 " %s." % sp.symbol)
            coeffs.append(c)
            dwfactors.append(debye_waller_factors.get(sp.symbol, 0))
            fcoords.append(site.frac_coords)
            occus.append(occu)
    zs = np.array(zs)
    coeffs = np.array(coeffs)
    fcoords = np.array(fcoords)
    occus = np.array(occus)
    dwfactors = np.array(dwfactors)

    # Store array of s^2 values since used multiple times.
    s2s = (g_hkls / 2) ** 2

    # Create array containing atomic scattering factors.
    # TODO: update this parameterisation to be Doyle-Turner
    fss = []
    for s2 in s2s:
        fs = zs - 41.78214 * s2 * np.sum(
            coeffs[:, :, 0] * np.exp(-coeffs[:, :, 1] * s2), axis=1)
        fss.append(fs)
    fss = np.array(fss)

    # Calculate structure factors for all excited g-vectors.
    f_hkls = []
    for n in np.arange(len(g_indices)):
        g = g_indices[n]
        fs = fss[n]
        dw_correction = np.exp(-dwfactors * s2s[n])
        f_hkl = np.sum(fs * occus * np.exp(2j * np.pi * np.dot(fcoords, g))
                       * dw_correction)
        f_hkls.append(f_hkl)
    f_hkls = np.array(f_hkls)

    # Define an intensity scaling that is linear with distance from Ewald sphere
    # along the beam direction.
    shape_factor = 1 - (excitation_error / maximum_excitation_error)

    # Calculate the peak intensities from the structure factor and excitation
    # error.
    peak_intensities = (f_hkls * f_hkls.conjugate()).real * shape_factor
    return peak_intensities


def equispaced_s2_grid(theta_range, phi_range, resolution=2.5, no_center=False):
    """Creates rotations approximately equispaced on a sphere.

    Parameters
    ----------
    theta_range : tuple of float
        (theta_min, theta_max)
        The range of allowable polar angles, in degrees.
    phi_range : tuple of float
        (phi_min, phi_max)
        The range of allowable azimuthal angles, in degrees.
    resolution : float
        The angular resolution of the grid in degrees.
    no_center : bool
        If true, `theta` values will not start at zero.

    Returns
    -------
    s2_grid : array-like
        Each row contains `(theta, phi)`, the azimthal and polar angle
        respectively.

    """
    theta_min, theta_max = [radians(t) for t in theta_range]
    phi_min, phi_max = [radians(r) for r in phi_range]
    resolution = radians(resolution)
    resolution = 2 * theta_max / int(Decimal(2 * theta_max / resolution).quantize(0, ROUND_HALF_UP))
    n_theta = int(Decimal((2 * theta_max / resolution + no_center)).quantize(0, ROUND_HALF_UP) / 2)

    if no_center:
        theta_grid = np.arange(0.5, n_theta + 0.5) * resolution
    else:
        theta_grid = np.arange(n_theta + 1) * resolution

    phi_grid = []
    for j, theta in enumerate(theta_grid):
        steps = max(round(sin(theta) * phi_max / theta_max * n_theta), 1)
        phi = phi_min\
            + np.arange(steps) * (phi_max - phi_min) / steps \
            + ((j+1) % 2) * (phi_max - phi_min) / steps / 2
        phi_grid.append(phi)
    s2_grid = np.array(
        [(theta, phi) for phis, theta in zip(phi_grid, theta_grid) for phi in
         phis])
    return s2_grid


def equispaced_so3_grid(alpha_max, beta_max, gamma_max, resolution=2.5,
                        alpha_min=0, beta_min=0, gamma_min=0):
    """Creates an approximately equispaced SO(3) grid.

    Parameters
    ----------
    alpha_max : float
    beta_max : float
    gamma_max : float
    resolution : float, optional
    alpha_min : float, optional
    beta_min : float, optional
    gamma_min : float, optional

    Returns
    -------
    so3_grid : array-like
        Each row contains `(alpha, beta, gamma)`, the three Euler angles on the
        SO(3) grid.

    """

    def no_center(res):
        if round(2 * pi / res) % 2 == 0:
            return True
        else:
            return False

    s2_grid = equispaced_s2_grid(
        (beta_min, beta_max),
        (alpha_min, alpha_max),
        resolution,
        no_center=no_center(radians(resolution))
    )

    gamma_min, gamma_max = radians(gamma_min), radians(gamma_max)
    gamma_max = gamma_max / 2
    resolution = radians(resolution)

    ap2 = int(np.round(2 * gamma_max / resolution))
    beta, alpha = s2_grid[:, 0], s2_grid[:, 1]
    real_part = np.cos(beta) * np.cos(alpha) + np.cos(alpha)
    imaginary_part = -(np.cos(beta) + 1) * np.sin(alpha)
    d_gamma = np.arctan2(imaginary_part, real_part)
    d_gamma = np.tile(d_gamma, (ap2, 1))
    gamma = -gamma_max + np.arange(ap2) * 2 * gamma_max / ap2
    gamma = (d_gamma + np.tile(gamma.T, (len(s2_grid), 1)).T).flatten()
    alpha = np.tile(alpha, (ap2, 1)).flatten()
    beta = np.tile(beta, (ap2, 1)).flatten()
    so3_grid = np.vstack((alpha, beta, gamma)).T
    return so3_grid


def astar_style_orientations(
        alpha_range: tuple,
        beta_range:  tuple,
        gamma_range: tuple,
        resolution:  float,
):
    grid = equispaced_s2_grid(beta_range, gamma_range, resolution)
    grid = [tuple(g) for g in grid]
    gamma = np.radians(np.arange(*alpha_range, resolution))
    orientations = np.array([(a, b, c) for a, (b, c) in itertools.product(gamma, grid)])
    return orientations
