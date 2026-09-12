"""Terrain (DGM) applications for BIMFabrikHH.

Two record-builder apps share a single :class:`TerrainMesh` input:

* :class:`TerrainBasicApp` — **deprecated**; use :class:`TerrainGenericApp`
  or :class:`TerrainRustApp`.
  Writes the mesh via ``ifcopenshell.api``.
* :class:`TerrainGenericApp` — writes the mesh via the ``ifcfactory``
  ``BIMFactoryElement`` pipeline (same pattern as ``TreesGenericApp``).
* :class:`TerrainRustApp` — ``bimfabrikhh_core_rs.terrain_to_ifc`` (same
  :class:`TerrainMesh`; Python still meshes).

The shared meshing helpers in
:mod:`BIMFabrikHH_core.apps.terrain.processing` produce the mesh (from
GeoTIFFs, optionally cropped to a bbox) and can be reused by any future
terrain impl.
"""

from BIMFabrikHH_core.data_models import Pset_Objektinformation_DGM, TerrainMesh

from .basic.app import TerrainBasicApp
from .generic.app import TerrainGenericApp
from .generic_rust import TerrainRustApp
from .landxml import export_terrain_landxml, terrain_mesh_to_landxml
from .processing import (
    GuideRing,
    adaptive_sampling,
    analyze_terrain_features,
    build_landuse_parts,
    collect_guide_rings,
    collect_guide_xy,
    cut_water_from_parts,
    generate_constrained_mesh,
    create_boundary_points,
    extract_mesh_adaptive,
    filter_and_add_boundary,
    generate_delaunay_mesh,
    merge_parcel_meshes,
    resolve_guide_records,
    sample_elevations_from_raster,
    split_mesh_by_nutzart,
)

__all__ = [
    "TerrainBasicApp",
    "TerrainGenericApp",
    "TerrainRustApp",
    "TerrainMesh",
    "Pset_Objektinformation_DGM",
    "adaptive_sampling",
    "analyze_terrain_features",
    "GuideRing",
    "build_landuse_parts",
    "resolve_guide_records",
    "collect_guide_rings",
    "collect_guide_xy",
    "cut_water_from_parts",
    "generate_constrained_mesh",
    "merge_parcel_meshes",
    "split_mesh_by_nutzart",
    "create_boundary_points",
    "extract_mesh_adaptive",
    "filter_and_add_boundary",
    "generate_delaunay_mesh",
    "sample_elevations_from_raster",
    "terrain_mesh_to_landxml",
    "export_terrain_landxml",
]
