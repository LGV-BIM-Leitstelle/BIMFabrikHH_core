"""
Basepoint Placement
===================

Unified helper for placing the project basepoint quad (the small
north-arrow pyramid that marks the project origin in EPSG:25832).

All apps (trees, terrain, city) historically carried their own slightly
different copy of this routine. This helper collapses them into one:

* Accepts an explicit ``basepoint_origin`` in the source CRS of the app's
  data (EPSG:25832 unless the app says otherwise). **If given, it wins.**
* Falls back to the lower-left corner of a WGS84 bounding box.
* Either way the origin ends up in the IFC output CRS given by
  ``transformer`` (EPSG:25832 without one).
* If neither is supplied, no basepoint is written and the function
  returns quietly.

The basepoint is built using the :class:`BIMFactoryElement` +
:class:`Transform` idiom (same as the generic apps) for a consistent
placement matrix and a single batched ``build`` call.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from ifcfactory import BIMFactoryElement, Transform

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.data_models.pydantic_georeferencing import BboxWgs84, horizontal_crs

from .advanced_objects import create_basepoint_quad


def basepoint_xy(
    *,
    basepoint_origin: Optional[Tuple[float, float]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    transformer: Optional[CoordinateTransformer] = None,
) -> Optional[Tuple[float, float]]:
    """Basepoint ``(x, y)`` in the output CRS, or ``None`` when neither input is given.

    ``basepoint_origin`` is in the source CRS of ``transformer`` and is
    transformed with it. Otherwise the lower-left of ``bbox_wgs84`` is
    reprojected into the target CRS of ``transformer``. Without a
    transformer the origin stays as given and the bbox lower-left goes to
    EPSG:25832, the default of apps without CRS handling.
    """
    if basepoint_origin is not None:
        x, y = float(basepoint_origin[0]), float(basepoint_origin[1])
        if transformer is not None:
            x, y, _ = transformer.transform_point(x, y)
        return x, y
    if bbox_wgs84 is not None:
        if transformer is None:
            bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)
            return float(bbox_epsg[0]), float(bbox_epsg[1])
        xs, ys = CoordinateTransformer(horizontal_crs(4326), transformer.target_crs).transform_xy_batch(
            [bbox_wgs84[0], bbox_wgs84[2]], [bbox_wgs84[1], bbox_wgs84[3]]
        )
        return min(xs), min(ys)
    return None


def place_basepoint(
    *,
    model: Any,
    site: Any,
    basepoint_origin: Optional[Tuple[float, float]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    size: float = 8.0,
    psets: Any = None,
    transformer: Optional[CoordinateTransformer] = None,
) -> None:
    """Create and position the project basepoint quad.

    Origin resolution (see :func:`basepoint_xy`):

    1. If ``basepoint_origin`` is given, use it. Explicit caller override.
    2. Else, if ``bbox_wgs84`` is given, use its lower-left corner.
    3. Else, skip silently — nothing is added to the model.

    The quad is written as an ``IfcBuildingElementProxy`` named
    ``"Nullpunktobjekt"`` (the default inside :func:`create_basepoint_quad`).

    Args:
        model: Target ``ifcopenshell.file`` model.
        site: ``IfcSite`` (or any spatial container) used as the parent
            ``inst`` of the basepoint ``BIMFactoryElement``.
        basepoint_origin: Explicit ``(x, y)`` in the source CRS of ``transformer``.
        bbox_wgs84: Fallback ``(min_lon, min_lat, max_lon, max_lat)``.
        size: Edge length of the basepoint quad in meters.
        psets: Pydantic pset groups (list, dict, or ``None``) forwarded
            to :func:`create_basepoint_quad` — attached to the quad.
        transformer: Output transformer of the app; ``None`` keeps EPSG:25832.
    """
    origin = basepoint_xy(basepoint_origin=basepoint_origin, bbox_wgs84=bbox_wgs84, transformer=transformer)
    if origin is None:
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


__all__ = ["basepoint_xy", "place_basepoint"]
