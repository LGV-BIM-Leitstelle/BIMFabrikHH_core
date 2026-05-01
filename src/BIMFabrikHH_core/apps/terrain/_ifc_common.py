"""Terrain-specific IFC-adjacent helpers.

Shared by :class:`TerrainBasicApp` and :class:`TerrainGenericApp`. Pure
mesh / coordinate math lives in
:mod:`BIMFabrikHH_core.apps.terrain.processing`; this module only
covers terrain-specific glue code between a :class:`TerrainMesh` and an
IFC model (default psets).

The basepoint-placement helper lives in
:func:`BIMFabrikHH_core.core.geometry.place_basepoint`. Request-bbox
reprojection to EPSG:25832 is
:func:`BIMFabrikHH_core.core.georeferencing.bbox_request_params_to_epsg25832`.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel

from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import Pset_Objektinformation_DGM


def default_terrain_psets() -> List[BaseModel]:
    """Template defaults for a DGM object (matches the BIM.HH DGM schema)."""
    return [Pset_Objektinformation_DGM(), default_bim_hamburg_hyperlink()]


__all__ = [
    "default_terrain_psets",
]
