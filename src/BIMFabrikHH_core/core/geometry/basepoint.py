"""
Basepoint Placement
===================

Unified helper for placing the project basepoint quad (the small
north-arrow pyramid that marks the project origin in EPSG:25832).

All apps (trees, terrain, city) historically carried their own slightly
different copy of this routine. This helper collapses them into one:

* Accepts an explicit ``basepoint`` ``(x, y, z)`` in the output CRS (e.g.
  entered by the user). **If given, it wins.**
* Else an explicit ``basepoint_origin`` in the source CRS of the app's
  data (EPSG:25832 unless the app says otherwise).
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

from typing import Any, Dict, Optional, Tuple

from ifcfactory import BIMFactoryElement, Transform

from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.model_creator.pset_utils import psets_to_wire
from BIMFabrikHH_core.data_models.pydantic_georeferencing import BboxWgs84, horizontal_crs

from .advanced_objects import convert_psets_from_dict, create_basepoint_quad


def basepoint_pset_values(psets: Optional[Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Nullpunktobjekt psets as ``{pset_name: {property: value}}`` for the Rust writers.

    ``psets`` is the dict of :func:`extract_psets_basepoint`. The values go
    through the same pset models (aliases, defaults) as the Python
    Nullpunktobjekt of :func:`create_basepoint_quad` and are typed by
    :func:`psets_to_wire` as ifcfactory would write them. Unknown psets are
    dropped; ``None`` or ``{}`` gives ``{}``.
    """
    return psets_to_wire(convert_psets_from_dict(psets or {}))


def basepoint_xyz(
    *,
    basepoint: Optional[Tuple[float, float, float]] = None,
    basepoint_origin: Optional[Tuple[float, float]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    transformer: Optional[CoordinateTransformer] = None,
) -> Optional[Tuple[float, float, float]]:
    """Basepoint ``(x, y, z)`` in the output CRS, or ``None`` when no input is given.

    ``basepoint`` is already in the output CRS (e.g. ``RequestParams.basepoint_xyz``)
    and wins as given. Otherwise, at height 0: ``basepoint_origin``, which is in
    the source CRS of ``transformer`` and is transformed with it, else the
    lower-left of ``bbox_wgs84`` reprojected into the target CRS of
    ``transformer``. Without a transformer the origin stays as given and the
    bbox lower-left goes to EPSG:25832, the default of apps without CRS handling.
    """
    if basepoint is not None:
        return float(basepoint[0]), float(basepoint[1]), float(basepoint[2])
    if basepoint_origin is not None:
        x, y = float(basepoint_origin[0]), float(basepoint_origin[1])
        if transformer is not None:
            x, y, _ = transformer.transform_point(x, y)
        return x, y, 0.0
    if bbox_wgs84 is not None:
        if transformer is None:
            bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)
            return float(bbox_epsg[0]), float(bbox_epsg[1]), 0.0
        xs, ys = CoordinateTransformer(horizontal_crs(4326), transformer.target_crs).transform_xy_batch(
            [bbox_wgs84[0], bbox_wgs84[2]], [bbox_wgs84[1], bbox_wgs84[3]]
        )
        return min(xs), min(ys), 0.0
    return None


def place_basepoint(
    *,
    model: Any,
    site: Any,
    basepoint: Optional[Tuple[float, float, float]] = None,
    basepoint_origin: Optional[Tuple[float, float]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    size: float = 8.0,
    psets: Any = None,
    transformer: Optional[CoordinateTransformer] = None,
) -> None:
    """Create and position the project basepoint quad.

    Origin resolution (see :func:`basepoint_xyz`):

    1. If ``basepoint`` is given, use it: ``(x, y, z)`` in the output CRS.
    2. Else, if ``basepoint_origin`` is given, use it at height 0.
    3. Else, if ``bbox_wgs84`` is given, use its lower-left corner at height 0.
    4. Else, skip silently — nothing is added to the model.

    The quad is written as an ``IfcBuildingElementProxy`` named
    ``"Nullpunktobjekt"`` (the default inside :func:`create_basepoint_quad`).

    Args:
        model: Target ``ifcopenshell.file`` model.
        site: ``IfcSite`` (or any spatial container) used as the parent
            ``inst`` of the basepoint ``BIMFactoryElement``.
        basepoint: ``(x, y, z)`` in the output CRS, ``z`` an absolute height.
        basepoint_origin: Explicit ``(x, y)`` in the source CRS of ``transformer``.
        bbox_wgs84: Fallback ``(min_lon, min_lat, max_lon, max_lat)``.
        size: Edge length of the basepoint quad in meters.
        psets: Pydantic pset groups (list, dict, or ``None``) forwarded
            to :func:`create_basepoint_quad` — attached to the quad.
        transformer: Output transformer of the app; ``None`` keeps EPSG:25832.
    """
    origin = basepoint_xyz(
        basepoint=basepoint, basepoint_origin=basepoint_origin, bbox_wgs84=bbox_wgs84, transformer=transformer
    )
    if origin is None:
        return

    BIMFactoryElement(
        inst=site,
        children=[
            Transform(
                translation=origin,
                item=create_basepoint_quad(size=size, psets=psets),
            ),
        ],
    ).build(model)


__all__ = ["basepoint_xyz", "place_basepoint"]
