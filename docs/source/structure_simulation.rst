Crystallographic Structure Simulation
=====================================

PyCrystEM makes use of the fantastic PyMatGen package to simulate and
manipulate crystal structures.

Creating a crystal structure
----------------------------

Structures are created using :class:`pycrystem.Lattice` and
   :class:`pycrystem.Structure`::

      >>> import pycrystem as pc
      >>> lattice = pc.Lattice.cubic(3.52)
      >>> coordinates = [[0.0, 0.0, 0.0],
                         [0.5, 0.5, 0.0],
                         [0.5, 0.0, 0.5],
                         [0.0, 0.5, 0.5]] # A face-centred cubic structure.
      >>> atoms = ["Ni", "Ni", "Ni", "Ni"]
      >>> structure = pc.Structure(lattice, atoms, coordinates)