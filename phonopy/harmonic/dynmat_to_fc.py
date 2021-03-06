# Copyright (C) 2014 Atsushi Togo
# All rights reserved.
#
# This file is part of phonopy.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# * Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in
#   the documentation and/or other materials provided with the
#   distribution.
#
# * Neither the name of the phonopy project nor the names of its
#   contributors may be used to endorse or promote products derived
#   from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import numpy as np
from phonopy.structure.atoms import PhonopyAtoms
from phonopy.structure.cells import get_supercell
from phonopy.harmonic.force_constants import distribute_force_constants
from phonopy.structure.cells import SNF3x3


def get_commensurate_points(supercell_matrix):  # wrt primitive cell
    """Commensurate q-points are returned.

    Parameters
    ----------
    supercell_matrix : array_like
        Supercell matrix with respect to primitive cell basis vectors.
        shape=(3, 3), dtype=int

    Returns
    -------
    commensurate_points : ndarray
        Commensurate points corresponding to supercell matrix.
        shape=(N, 3), dtype='double', order='C'
        where N = det(supercell_matrix)

    """

    smat = np.array(supercell_matrix, dtype=int)
    rec_primitive = PhonopyAtoms(numbers=[1],
                                 scaled_positions=[[0, 0, 0]],
                                 cell=np.diag([1, 1, 1]),
                                 pbc=True)
    rec_supercell = get_supercell(rec_primitive, smat.T)
    q_pos = rec_supercell.scaled_positions
    return np.array(np.where(q_pos > 1 - 1e-15, q_pos - 1, q_pos),
                    dtype='double', order='C')


def get_commensurate_points_in_integers(supercell_matrix):
    """Commensurate q-points in integer representation are returned.

    A set of integer representation of lattice points is transformed to
    the equivalent set of lattice points in fractional coordinates with
    respect to supercell basis vectors by
        integer_lattice_points / det(supercell_matrix)

    Parameters
    ----------
    supercell_matrix : array_like
        Supercell matrix with respect to primitive cell basis vectors.
        shape=(3, 3)
        dtype=intc

    Returns
    -------
    lattice_points : ndarray
        Integer representation of lattice points in supercell.
        shape=(N, 3)

    """
    smat = np.array(supercell_matrix, dtype=int)
    snf = SNF3x3(smat.T)
    snf.run()
    D = snf.A.diagonal()
    b, c, a = np.meshgrid(range(D[1]), range(D[2]), range(D[0]))
    lattice_points = np.dot(np.c_[a.ravel() * D[1] * D[2],
                                  b.ravel() * D[0] * D[2],
                                  c.ravel() * D[0] * D[1]], snf.Q.T)
    lattice_points = np.array(lattice_points % np.prod(D),
                              dtype='intc', order='C')
    return lattice_points


class DynmatToForceConstants(object):
    """Transforms eigensolutions to force constants

    This is the inverse transform of force constants to eigensolutions.
    Eigenvalue-eigenvector pairs or frequency-eigenvector pairs of
    dynamical matrices are transformed to force constants by this class.
    Optionally, dynamical matrices (not the DynamicalMatrix class instance,
    but the calculated matrices) can be used instead of above pairs.

    The eigensolutions have to be those calculated at commensurate q-points
    of supercell matrix. The commensurate q-points are obtained by the
    attribute ``commensurate_points``. This set of commensurate points can be
    also given by setter of it.

    One supposed usage is::

       d2f = DynmatToForceConstants(primitive, supercell)
       comm_points = d2f.commensurate_points
       ... calculated phonons at comm_points
       d2f.create_dynamical_matrices(frequencies=frequencies,
                                     eigenvectors=eigenvectors)
       d2f.run()
       fc = d2f.force_constants

    Another usage may be with eigensolutions at commensurate q-points::

       d2f = DynmatToForceConstants(primitive, supercell,
                                    commensurate_points=comm_points,
                                    eigenvalues=eigenvalues,
                                    eigenvectors=eigenvectors)
       d2f.run()
       fc = d2f.force_constants


    Attributes
    ----------
    force_constants : ndarray
        Calculated force constants. Only getter. Array shape depends on
        ``is_full_fc``.
            True : shape=(supercell_atoms, supercell_atoms, 3, 3)
            False : shape=(primitive_atoms, supercell_atoms, 3, 3)
        Default is True.
        dtype='double', order='C'.
    commensurate_points : ndarray
        Commensurate q-points of supercell matrix.
        shape=(det(supercell_matrix), 3), dtype='double', order='C'.
    dynamical_matrices : ndarray
        shape=(det(supercell_matrix), num_band, num_band),
        where num_band is 3 x number of atoms in primitive cell.
        dtype='complex128', order='C'.

    """

    def __init__(self,
                 primitive,
                 supercell,
                 frequencies=None,
                 eigenvalues=None,
                 eigenvectors=None,
                 dynamical_matrices=None,
                 commensurate_points=None,
                 is_full_fc=True):
        """

        Note
        ----
        When calculating force constants from eigensolutions,
        eigher one of frequency-eigenvector pair or eigenvalu-eigenvector
        can be used.

        Parameters
        ----------
        supercell : Supercell
            Supercell.
        primitive : Primitive
            Primitive cell
        frequencies : ndarray
            Phonon frequencies as the solution of dynamical matrices at
            commensurate q-points.
            shape=(det(supercell_matrix), num_band), dtype='double', order='C'
            where ``num_band`` is 3 x number of atoms in primitive cell.
        eigenvalues : ndarray
            Phonon eigenvalues as the solution of dynamical matrices at
            commensurate q-points.
            shape=(det(supercell_matrix), num_band), dtype='double', order='C'
            where ``num_band`` is 3 x number of atoms in primitive cell.
        eigenvectors : ndarray
            Phonon eigenvectors as the solution of dynamical matrices at
            commensurate q-points.
            shape=(det(supercell_matrix), num_band, num_band)
            dtype='complex128', order='C'.
            where ``num_band`` is 3 x number of atoms in primitive cell.
        dynamical_matrices : ndarray
            Dynamical matrices at commensurate q-points.
            shape=(det(supercell_matrix), num_band, num_band)
            dtype='complex128', order='C'.
            where ``num_band`` is 3 x number of atoms in primitive cell.
        commensurate_points : ndarray
            Commensurate q-points corresponding to supercell_matrix. The order
            has to be the same as those of frequencies or eigenvalues, and
            eigenvectors. As the default behaviour, commensurate q-points are
            generated when this is not given.
            shape=(det(supercell_matrix), 3), dtype='double', order='C'
        is_full_fc : bool
            This controls the matrix shape of calculated force constants.
            True and False give the full and compact force cosntants,
            respectively. The default is True. See more details in Attributes
            section of this class.

        """
        self._primitive = primitive
        self._supercell = supercell
        supercell_matrix = np.linalg.inv(self._primitive.primitive_matrix)
        supercell_matrix = np.rint(supercell_matrix).astype('intc')
        if commensurate_points is None:
            self._commensurate_points = get_commensurate_points(
                supercell_matrix)
        else:
            self._commensurate_points = commensurate_points
        (self._shortest_vectors,
         self._multiplicity) = primitive.get_smallest_vectors()
        self._dynmat = None
        n_s = self._supercell.get_number_of_atoms()
        n_p = self._primitive.get_number_of_atoms()
        if is_full_fc:
            fc_shape = (n_s, n_s, 3, 3)
        else:
            fc_shape = (n_p, n_s, 3, 3)
        self._fc = np.zeros(fc_shape, dtype='double', order='C')

        itemsize = self._fc.itemsize
        self._dtype_complex = ("c%d" % (itemsize * 2))

        if ((frequencies is not None or eigenvalues is not None)
            and eigenvectors is not None):
            self.create_dynamical_matrices(
                frequencies=frequencies,
                eigenvalues=eigenvalues,
                eigenvectors=eigenvectors)
        elif dynamical_matrices is not None:
            self.dynamical_matrices = dynamical_matrices

    def run(self):
        self._inverse_transformation()
        # Full fc
        # self._distribute_force_constants()

    @property
    def force_constants(self):
        return self._fc

    def get_force_constants(self):
        return self.force_constants

    @property
    def commensurate_points(self):
        return self._commensurate_points

    def get_commensurate_points(self):
        return self.commensurate_points

    @commensurate_points.setter
    def commensurate_points(self, comm_points):
        self._commensurate_points = np.array(
            comm_points, dtype='double', order='C')

    @property
    def dynamical_matrices(self):
        return self._dynmat

    def get_dynamical_matrices(self):
        return self.dynamical_matrices

    @dynamical_matrices.setter
    def dynamical_matrices(self, dynmat):
        self._dynmat = np.array(dynmat, dtype=self._dtype_complex, order='C')

    def set_dynamical_matrices(self, dynmat):
        self.dynamical_matrices = dynmat

    def create_dynamical_matrices(self,
                                  frequencies=None,
                                  eigenvalues=None,
                                  eigenvectors=None):
        dm = []
        if eigenvalues is not None:
            for eigvals, eigvecs in zip(eigenvalues, eigenvectors):
                dm.append(np.dot(np.dot(eigvecs, np.diag(eigvals)),
                                 eigvecs.T.conj()))
        else:
            for freqs, eigvecs in zip(frequencies, eigenvectors):
                eigvals = freqs ** 2 * np.sign(freqs)
                dm.append(np.dot(np.dot(eigvecs, np.diag(eigvals)),
                                 eigvecs.T.conj()))

        self.dynamical_matrices = dm

    def _inverse_transformation(self):
        try:
            import phonopy._phonopy as phonoc
            self._c_inverse_transformation()
        except ImportError:
            self._py_inverse_transformation()

        if self._fc.shape[0] == self._fc.shape[1]:
            distribute_force_constants_by_translations(self._fc,
                                                       self._primitive,
                                                       self._supercell)

    def _c_inverse_transformation(self):
        import phonopy._phonopy as phonoc

        s2p = self._primitive.s2p_map
        p2p = self._primitive.p2p_map
        s2pp = np.array([p2p[i] for i in s2p], dtype='intc')

        if self._fc.shape[0] == self._fc.shape[1]:
            fc_index_map = self._primitive.p2s_map
        else:
            fc_index_map = np.arange(self._fc.shape[0], dtype='intc')

        phonoc.transform_dynmat_to_fc(self._fc,
                                      self._dynmat.view(dtype='double'),
                                      self._commensurate_points,
                                      self._shortest_vectors,
                                      self._multiplicity,
                                      self._primitive.masses,
                                      s2pp,
                                      fc_index_map)

    def _py_inverse_transformation(self):
        s2p = self._primitive.s2p_map
        p2s = self._primitive.p2s_map
        p2p = self._primitive.p2p_map

        m = self._primitive.masses
        N = (self._supercell.get_number_of_atoms() /
             self._primitive.get_number_of_atoms())

        for p_i, s_i in enumerate(p2s):
            for s_j, p_j in enumerate([p2p[i] for i in s2p]):
                coef = np.sqrt(m[p_i] * m[p_j]) / N
                fc_elem = self._sum_q(p_i, s_j, p_j) * coef
                if self._fc.shape[0] == self._fc.shape[1]:
                    self._fc[s_i, s_j] = fc_elem
                else:
                    self._fc[p_i, s_j] = fc_elem

    def _sum_q(self, p_i, s_j, p_j):
        multi = self._multiplicity[s_j, p_i]
        pos = self._shortest_vectors[s_j, p_i, :multi]
        sum_q = np.zeros((3, 3), dtype=self._dtype_complex, order='C')
        phases = -2j * np.pi * np.dot(self._commensurate_points, pos.T)
        phase_factors = np.exp(phases).sum(axis=1) / multi
        for i, coef in enumerate(phase_factors):
            sum_q += self._dynmat[i,
                                  (p_i * 3):(p_i * 3 + 3),
                                  (p_j * 3):(p_j * 3 + 3)] * coef
        return sum_q.real


def distribute_force_constants_by_translations(fc, primitive, supercell):
    s2p = primitive.get_supercell_to_primitive_map()
    p2s = primitive.get_primitive_to_supercell_map()
    positions = supercell.get_scaled_positions()
    lattice = supercell.get_cell().T
    diff = positions - positions[p2s[0]]
    trans = np.array(diff[np.where(s2p == p2s[0])[0]],
                     dtype='double', order='C')
    rotations = np.array([np.eye(3, dtype='intc')] * len(trans),
                         dtype='intc', order='C')
    permutations = primitive.get_atomic_permutations()
    distribute_force_constants(fc,
                               p2s,
                               lattice,
                               rotations,
                               permutations)
