"""City-specific IFC-adjacent helpers.

Shared by :class:`CityBasicApp` and :class:`CityGenericApp`. Pure
CityGML / filtering math lives in
:mod:`BIMFabrikHH_core.apps.city.processing`; this module holds the
polygon-mesh helpers that both apps need for LoD2 surfaces.

The basepoint-placement helper that used to live here has been promoted
to :func:`BIMFabrikHH_core.core.geometry.place_basepoint` and is shared
by every app.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple


def clean_polygon_ring(indices: Sequence[int]) -> List[int]:
    """Strip closing repeats and consecutive duplicates from a polygon ring.

    IFC ``IfcIndexedPolygonalFace`` / ``IfcIndexedPolygonalFaceWithVoids``
    require unique aggregate elements (``SYNTAX_VALIDATION_48``), so any
    explicit closing vertex (``ring[-1] == ring[0]``) as well as any
    adjacent duplicates are dropped.

    Args:
        indices: Raw vertex-index sequence for a single ring.

    Returns:
        A new ``list`` with duplicates removed. An empty input returns
        an empty list.
    """
    if not indices:
        return []
    ring = list(indices)
    if len(ring) > 1 and ring[-1] == ring[0]:
        ring = ring[:-1]
    cleaned: List[int] = [ring[0]]
    for idx in ring[1:]:
        if idx != cleaned[-1]:
            cleaned.append(idx)
    return cleaned


def parse_face_with_voids(
    entry: Any,
    *,
    index_offset: int = 0,
) -> Optional[Tuple[List[int], List[List[int]]]]:
    """Parse one ``Building.faces_with_voids`` entry into ``(outer, inners)``.

    :class:`BIMFabrikHH_core.data_models.pydantic_psets_city_model.Building`
    stores face-with-voids entries as dicts in two shapes:

    - ``{"type": "IfcIndexedPolygonalFaceWithVoids", "coord_index": [...],
      "inner_coord_indices": [[...], [...]]}`` — a face with one or more
      inner rings (courtyard / atrium).
    - ``{"type": "IfcIndexedPolygonalFace", "coord_index": [...]}`` — a
      plain face without voids (kept in the same list for ordering).

    Rings are cleaned with :func:`clean_polygon_ring` and rings with less
    than three vertices are dropped. ``index_offset`` is added to every
    index (e.g. ``+1`` when converting 0-based to IFC's 1-based indexing).

    Args:
        entry: Single entry from ``Building.faces_with_voids``. May also
            be a raw index sequence (used as the outer ring).
        index_offset: Integer added to every vertex index.

    Returns:
        ``(outer, inners)`` where ``outer`` has at least three indices
        and ``inners`` is a list of inner rings (possibly empty).
        Returns ``None`` when the outer ring is degenerate.
    """
    outer_raw: Sequence[int]
    inner_raw: List[Sequence[int]]

    if isinstance(entry, dict):
        outer_raw = entry.get("coord_index") or []
        inner_raw = list(entry.get("inner_coord_indices") or [])
    else:
        outer_raw = list(entry)
        inner_raw = []

    def _offset(ring: Sequence[int]) -> List[int]:
        cleaned = clean_polygon_ring(ring)
        if index_offset:
            cleaned = [i + index_offset for i in cleaned]
        return cleaned

    outer = _offset(outer_raw)
    if len(outer) < 3:
        return None
    inners = [r for r in (_offset(ring) for ring in inner_raw) if len(r) >= 3]
    return outer, inners


def parse_building_faces(
    faces: Optional[Sequence[Sequence[int]]],
    faces_with_voids: Optional[Sequence[Dict[str, Any]]],
    *,
    index_offset: int = 0,
) -> List[Tuple[List[int], List[List[int]]]]:
    """Merge ``Building.faces`` and ``.faces_with_voids`` into a canonical shape.

    Each returned tuple is ``(outer, inners)`` where ``inners`` is empty
    for plain faces. All rings are already cleaned and offset-adjusted,
    and degenerate rings are dropped.
    """
    out: List[Tuple[List[int], List[List[int]]]] = []

    for ring in faces or []:
        cleaned = clean_polygon_ring(ring)
        if index_offset:
            cleaned = [i + index_offset for i in cleaned]
        if len(cleaned) >= 3:
            out.append((cleaned, []))

    for entry in faces_with_voids or []:
        parsed = parse_face_with_voids(entry, index_offset=index_offset)
        if parsed is not None:
            out.append(parsed)

    return out


__all__ = [
    "clean_polygon_ring",
    "parse_face_with_voids",
    "parse_building_faces",
]
