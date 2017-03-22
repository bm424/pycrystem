Simulating electron diffraction
===============================

.. image:: _static/diffraction_simulation.png
   :width: 500px
   :align: center
   :alt: Two visualisations of a simulated pattern for cubic GaAs.


For a wide variety of electron diffraction analysis it is useful to be able
to simulate electron diffraction patterns for comparison or validation.
Electron diffraction simulations are made available through PyCrystEM.

Ultimately multiple simulation tools will be made available covering various
applications but at present only the simplest methods are implemented. All
methods are available through the ElectronDiffractionGenerator class.

Kinematical simulation of spot patterns
---------------------------------------

Kinematical simulation of spot diffraction patterns is implemented as described
in numerous textbooks. In PyCrystEM, several simple steps are required.

1. Create a structure to simulate (see :doc:`structure_simulation`).
2. Create a generator using  :class:`~pycrystem.ElectronDiffractionGenerator`,
   specifying the acceleration voltage and the excitation error::

      >>> generator = pc.ElectronDiffractionGenerator(300, 0.1)

3. The generator can then be used to simulate the pattern of the structure::

      >>> simulated_pattern = generator.calculate_ed_data(structure, 1.5)

In brief, patterns are simulated by constructing a reciprocal lattice for
the structure, finding the intersection with an appropriate Ewald sphere,
and calculating the intensities based on the structure factor of the
intersecting peaks and the excitation error (currently modeled as a simple
linear decrease from the center of the rel rod to the end).

Visualisation
-------------

The simulated pattern can be visualised either abstractly or as a signal.::

    >>> simulated_pattern.plot()

will produce a plot clearly showing peak positions and intensities.::

    >>> simulated_pattern.as_signal((144, 144), 1., 1.5).plot()

produces and plots a simulated signal, modelling the peaks as Gaussians.