"""Terrain (DGM) applications for BIMFabrikHH.

Two record-builder apps share a single :class:`TerrainMesh` input:

* :class:`TerrainBasicApp` — writes the mesh via ``ifcopenshell.api``.
* :class:`TerrainGenericApp` — writes the mesh via the ``ifcfactory``
  ``BIMFactoryElement`` pipeline (same pattern as ``TreesGenericApp``).

The shared meshing helpers in
:mod:`BIMFabrikHH_core.apps.terrain.processing` produce the mesh (from
GeoTIFFs, optionally cropped to a bbox) and can be reused by any future
terrain impl.
"""

from BIMFabrikHH_core.data_models import Pset_Objektinformation_DGM, TerrainMesh

from .basic.app import TerrainBasicApp
from .generic.app import TerrainGenericApp
from .processing import (
    adaptive_sampling,
    analyze_terrain_features,
    create_boundary_points,
    extract_mesh_adaptive,
    filter_and_add_boundary,
    generate_delaunay_mesh,
    sample_elevations_from_raster,
)

__all__ = [
    "TerrainBasicApp",
    "TerrainGenericApp",
    "TerrainMesh",
    "Pset_Objektinformation_DGM",
    "adaptive_sampling",
    "analyze_terrain_features",
    "create_boundary_points",
    "extract_mesh_adaptive",
    "filter_and_add_boundary",
    "generate_delaunay_mesh",
    "sample_elevations_from_raster",
]
