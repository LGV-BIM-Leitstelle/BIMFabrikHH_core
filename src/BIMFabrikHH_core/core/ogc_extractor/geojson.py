"""GeoJSON FeatureCollection helpers for Hamburg OGC API–style responses."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

# Minimum positions: polygon exterior must be closed (first == last) → at least 4 positions in GeoJSON.
_MIN_POLYGON_EXTERIOR_POSITIONS: int = 4
_MIN_LINESTRING_POSITIONS: int = 2


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


def positions_to_xy_ring(positions: List[Any]) -> List[Tuple[float, float]]:
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


def parse_feature_polygon_exterior_ring(feature: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """Exterior ring of the first polygon on the feature, or ``None`` if not applicable."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") != "Polygon":
        return None
    coords = geom.get("coordinates")
    if not coords or not isinstance(coords[0], list):
        return None
    ring = positions_to_xy_ring(coords[0])
    if len(ring) < _MIN_POLYGON_EXTERIOR_POSITIONS:
        return None
    return ring


def parse_feature_linestring_path(feature: Dict[str, Any]) -> Optional[List[Tuple[float, float]]]:
    """Vertices of a ``LineString`` geometry, or ``None``."""
    geom = feature.get("geometry")
    if not isinstance(geom, dict) or geom.get("type") != "LineString":
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, list):
        return None
    path = positions_to_xy_ring(coords)
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
        path = positions_to_xy_ring(line)
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
    "parse_feature_polygon_exterior_ring",
    "positions_to_xy_ring",
]
