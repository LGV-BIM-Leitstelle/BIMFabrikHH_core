"""Terrain-specific IFC-adjacent helpers.

Shared by :class:`TerrainBasicApp` and :class:`TerrainGenericApp`. Pure
mesh / coordinate math lives in
:mod:`BIMFabrikHH_core.apps.terrain.processing`; this module only
covers terrain-specific glue code between a :class:`TerrainMesh` and an
IFC model (bbox resolution, fallback nullpunkt, default psets).

The basepoint-placement helper that used to live here has been promoted
to :func:`BIMFabrikHH_core.core.geometry.place_basepoint` and is shared
by every app.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel

from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import Pset_Objektinformation_DGM


def resolve_bbox_utm(
    request_params: RequestParams,
) -> Optional[Tuple[float, float, float, float]]:
    """Project the request-params WGS84 bbox into EPSG:25832, if present."""
    bbox_wgs84 = request_params.bbox_as_wgs84_tuple
    if bbox_wgs84 is None:
        return None
    return bbox_wgs84_to_epsg25832(bbox_wgs84)


def fallback_nullpunkt(vertices: List[List[float]]) -> Tuple[float, float]:
    """Minimum ``(x, y)`` over all vertices — used when no nullpunkt is set."""
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    return (min(xs) if xs else 0.0, min(ys) if ys else 0.0)


def default_terrain_psets() -> List[BaseModel]:
    """Template defaults for a DGM object (matches the BIM.HH DGM schema)."""
    return [Pset_Objektinformation_DGM(), default_bim_hamburg_hyperlink()]


__all__ = [
    "resolve_bbox_utm",
    "fallback_nullpunkt",
    "default_terrain_psets",
]
