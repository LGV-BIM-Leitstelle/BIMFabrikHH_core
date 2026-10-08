"""GeoJSON FeatureCollection helpers for Hamburg OGC API–style responses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union, TypeAlias

# Minimum positions: polygon exterior must be closed (first == last) → at least 4 positions in GeoJSON.
_MIN_POLYGON_EXTERIOR_POSITIONS: int = 4
_MIN_LINESTRING_POSITIONS: int = 2

Coordinate: TypeAlias = Tuple[float, float]
Ring: TypeAlias = List[Coordinate]

@dataclass
class Polygon:
    exterior: Ring
    holes: List[Ring]

MultiPolygon = List[Polygon]


def ensure_feature_collection(data: Any) -> Dict[str, Any]:
    """Return ``data`` if it is a GeoJSON FeatureCollection object, else raise."""
    if not isinstance(data, dict):
        raise ValueError("GeoJSON root must be a JSON object")
    if data.get("type") != "FeatureCollection":
        raise ValueError("Expected type 'FeatureCollection'")
    return data


def iter_geojson_features(data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    """Yield ``Feature`` objects from a FeatureCollection dict (skip non-dicts / wrong type)."""
    for feat in data.get("features") or []:
        if isinstance(feat, dict) and feat.get("type") == "Feature":
            yield feat


def positions_to_xy_line(positions: List[Any]) -> List[Tuple[float, float]]:
    """Normalize a GeoJSON position sequence to ``(x, y)`` floats (ignore Z/M if present)."""
    out: List[Tuple[float, float]] = []
    for pt in positions:
        if not isinstance(pt, (list, tuple)) or len(pt) < 2:
            continue
        out.append((float(pt[0]), float(pt[1])))
    return out


def geojson_feature_properties(feature: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return ``feature['properties']`` when it is a dict, else ``None``."""
    props = feature.get("properties")
    return props if isinstance(props, dict) else None


def feature_identifier(feature: Dict[str, Any], *, fallback: str) -> Union[str, int]:
    """Return ``feature['id']`` or ``fallback`` when missing."""
    fid = feature.get("id")
    return fid if fid is not None else fallback


def feature_geometry_type(feature: Dict[str, Any]) -> str | None:
    """Geometry type of a feature."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict):
        return None
    return geom.get("type")


def parse_feature_polygons(feature: Dict[str, Any]) -> List[List[List[Tuple[float, float]]]]:
    """``Polygon`` / ``MultiPolygon`` coordinates in the feature."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict):
        return []
    geom_type = geom.get("type")
    coords = geom.get("coordinates")
    polygons: List[List[List[Tuple[float, float]]]] = []
    if geom_type == "Polygon":
        polygons = [coords] if isinstance(coords, list) else []
    elif geom_type == "MultiPolygon":
        polygons = coords if isinstance(coords, list) else []
    else:
        return []
    return polygons


def parse_feature_all_rings(feature: Dict[str, Any]) -> MultiPolygon:
    """Exterior rings and holes of every ``Polygon`` / ``MultiPolygon`` part in the feature."""
    polygons = parse_feature_polygons(feature)

    multipolygon: MultiPolygon = []

    for polygon in polygons:
        rings = extract_all_rings_from_polygon(polygon)
        if rings:
            multipolygon.append(rings)
    
    return multipolygon


def extract_all_rings_from_polygon(polygon: List[List[Tuple[float, float]]]) -> Polygon | None:
    """Exterior rings and interior rings (holes) of one polygon."""
    exterior_ring: Ring
    holes: list[Ring] = []
    if not isinstance(polygon, list):
        return None

    for index, ring in enumerate(polygon):
        if not ring or not isinstance(ring, list):
            continue
        ring_xy = positions_to_xy_line(ring)
        if len(ring_xy) < _MIN_POLYGON_EXTERIOR_POSITIONS:
            continue
        if index == 0:
            exterior_ring = ring_xy
        else:
            holes.append(ring_xy)

    rings = Polygon(exterior=exterior_ring, holes=holes)
    return rings


def parse_feature_polygon_first_exterior_ring(feature: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """Exterior ring of the first polygon on the feature, or ``None`` if not applicable."""
    rings = parse_feature_polygon_exterior_rings(feature)
    return rings[0] if rings else None


def parse_feature_polygon_exterior_rings(feature: Dict[str, Any]) -> List[List[Tuple[float, float]]]:
    """Exterior rings of every ``Polygon`` / ``MultiPolygon`` part (holes ignored)."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict):
        return []
    geom_type = geom.get("type")
    coords = geom.get("coordinates")
    polygons: List[Any] = []
    if geom_type == "Polygon":
        polygons = [coords] if isinstance(coords, list) else []
    elif geom_type == "MultiPolygon":
        polygons = coords if isinstance(coords, list) else []
    else:
        return []

    rings: List[List[Tuple[float, float]]] = []
    for poly in polygons:
        if not poly or not isinstance(poly, list) or not isinstance(poly[0], list):
            continue
        ring = positions_to_xy_line(poly[0])
        if len(ring) >= _MIN_POLYGON_EXTERIOR_POSITIONS:
            rings.append(ring)
    return rings


def parse_feature_point(feature: Dict[str, Any]) -> Tuple[float, float] | None:
    """Vertices of a ``Point`` geometry, or ``None``."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") != "Point":
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        return None
    return (float(coords[0]), float(coords[1]))


def parse_feature_linestring_path(feature: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """Vertices of a ``LineString`` geometry, or ``None``."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") != "LineString":
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, list):
        return None
    path = positions_to_xy_line(coords)
    if len(path) < _MIN_LINESTRING_POSITIONS:
        return None
    return path


def parse_feature_multilinestring_paths(feature: Dict[str, Any]) -> List[List[Tuple[float, float]]]:
    """Each ``LineString`` in a ``MultiLineString`` as its own vertex list (may be empty)."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") != "MultiLineString":
        return []
    coords = geom.get("coordinates")
    if not isinstance(coords, list):
        return []
    paths: List[List[Tuple[float, float]]] = []
    for line in coords:
        if not isinstance(line, list):
            continue
        path = positions_to_xy_line(line)
        if len(path) >= _MIN_LINESTRING_POSITIONS:
            paths.append(path)
    return paths


__all__ = [
    "ensure_feature_collection",
    "feature_identifier",
    "geojson_feature_properties",
    "iter_geojson_features",
    "parse_feature_linestring_path",
    "parse_feature_multilinestring_paths",
    "parse_feature_polygon_first_exterior_ring",
    "parse_feature_polygon_exterior_rings",
    "positions_to_xy_line",

]
