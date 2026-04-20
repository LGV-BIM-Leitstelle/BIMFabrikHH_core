"""
Basepoint Placement
===================

Unified helper for placing the project basepoint quad (the small
north-arrow pyramid that marks the project origin in EPSG:25832).

All apps (trees, terrain, city) historically carried their own slightly
different copy of this routine. This helper collapses them into one:

* Accepts an explicit ``basepoint_origin`` in the project CRS
  (EPSG:25832). **If given, it wins.**
* Falls back to the lower-left corner of a WGS84 bounding box,
  reprojected into EPSG:25832 (the city apps' historical default).
* If neither is supplied, no basepoint is written and the function
  returns quietly — callers that want to force a placement should
  pre-resolve their own "app default" origin (e.g. terrain apps pass
  ``mesh.nullpunkt``).

The basepoint is built using the :class:`BIMFactoryElement` +
:class:`Transform` idiom (same as the generic apps) for a consistent
placement matrix and a single batched ``build`` call.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from ifcfactory import BIMFactoryElement, Transform

from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832

from .advanced_objects import create_basepoint_quad

BboxWgs84 = Tuple[float, float, float, float]


def place_basepoint(
    *,
    model: Any,
    site: Any,
    basepoint_origin: Optional[Tuple[float, float]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    size: float = 8.0,
    psets: Any = None,
) -> None:
    """Create and position the project basepoint quad.

    Origin resolution:

    1. If ``basepoint_origin`` is given, use it as the ``(x, y)`` in the
       project CRS (EPSG:25832). Explicit caller override.
    2. Else, if ``bbox_wgs84`` is given, use its lower-left corner
       reprojected WGS84 → EPSG:25832.
    3. Else, skip silently — nothing is added to the model.

    The quad is written as an ``IfcBuildingElementProxy`` named
    ``"Nullpunktobjekt"`` (the default inside :func:`create_basepoint_quad`).

    Args:
        model: Target ``ifcopenshell.file`` model.
        site: ``IfcSite`` (or any spatial container) used as the parent
            ``inst`` of the basepoint ``BIMFactoryElement``.
        basepoint_origin: Explicit ``(x, y)`` in EPSG:25832.
        bbox_wgs84: Fallback ``(min_lon, min_lat, max_lon, max_lat)``.
        size: Edge length of the basepoint quad in meters.
        psets: Pydantic pset groups (list, dict, or ``None``) forwarded
            to :func:`create_basepoint_quad` — attached to the quad.
    """
    if basepoint_origin is not None:
        origin = (float(basepoint_origin[0]), float(basepoint_origin[1]))
    elif bbox_wgs84 is not None:
        bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)
        origin = (float(bbox_epsg[0]), float(bbox_epsg[1]))
    else:
        return

    BIMFactoryElement(
        inst=site,
        children=[
            Transform(
                translation=(origin[0], origin[1], 0.0),
                item=create_basepoint_quad(size=size, psets=psets),
            ),
        ],
    ).build(model)


__all__ = ["place_basepoint", "BboxWgs84"]
