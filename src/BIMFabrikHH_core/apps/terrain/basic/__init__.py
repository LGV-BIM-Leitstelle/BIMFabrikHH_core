"""Deprecated. Use :class:`TerrainGenericApp` or :class:`TerrainRustApp`.

Basic terrain IFC export (feature-preserving adaptive-sampled Delaunay mesh).
"""

from BIMFabrikHH_core.data_models import Pset_Objektinformation_DGM, TerrainMesh

from .app import TerrainBasicApp

__all__ = ["TerrainBasicApp", "TerrainMesh", "Pset_Objektinformation_DGM"]
