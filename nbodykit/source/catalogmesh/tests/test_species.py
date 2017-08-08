from runtests.mpi import MPITest
from nbodykit.lab import *
from nbodykit import setup_logging

from numpy.testing import assert_array_equal, assert_allclose
import pytest

setup_logging()

@MPITest([1, 4])
def test_getitem(comm):

    CurrentMPIComm.set(comm)

    # the catalog
    source1 = UniformCatalog(nbar=3e-5, BoxSize=512., seed=42)
    source2 = UniformCatalog(nbar=3e-5, BoxSize=512., seed=84)
    cat = MultipleSpeciesCatalog(['data', 'randoms'], source1, source2, use_cache=True)

    # the mesh
    mesh = cat.to_mesh(Nmesh=32, BoxSize=512)

    for source, name in zip([source1, source2], ['data', 'randoms']):
        submesh = mesh[name] # should be equal to source
        for col in source:
            assert col in submesh
            assert_array_equal(submesh[col].compute(), source[col].compute())

@MPITest([1, 4])
def test_paint(comm):

    CurrentMPIComm.set(comm)

    # the catalog
    source1 = UniformCatalog(nbar=3e-5, BoxSize=512., seed=42)
    source2 = UniformCatalog(nbar=3e-5, BoxSize=512., seed=84)
    cat = MultipleSpeciesCatalog(['data', 'randoms'], source1, source2, use_cache=True)

    # the meshes
    mesh = cat.to_mesh(Nmesh=32, BoxSize=512)
    mesh1 = source1.to_mesh(Nmesh=32, BoxSize=512)
    mesh2 = source2.to_mesh(Nmesh=32, BoxSize=512)

    # paint
    real1 = mesh1.to_real_field()
    real2 = mesh2.to_real_field()

    # un-normalize real1 and real2
    real1[:] *= real1.attrs['num_per_cell']
    real2[:] *= real2.attrs['num_per_cell']
    norm = real1.attrs['num_per_cell'] + real2.attrs['num_per_cell']

    # the combined density field
    combined = mesh.to_real_field()

    # must be the same
    assert_allclose(combined.value, (real1.value + real2.value)/norm, atol=1e-5)
