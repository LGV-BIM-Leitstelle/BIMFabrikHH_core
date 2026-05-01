from typing import Optional, Tuple

from pyproj import Transformer

from BIMFabrikHH_core.data_models.params_tree import RequestParams


def bbox_wgs84_to_epsg25832(bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """
    Convert a bounding box from WGS84 (EPSG:4326) to EPSG:25832.
    Args:
        bbox: (minx, miny, maxx, maxy) in WGS84 (longitude, latitude)
    Returns:
        (minx, miny, maxx, maxy) in EPSG:25832
    """
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    # Transform all four corners
    x1, y1 = transformer.transform(bbox[0], bbox[1])
    x2, y2 = transformer.transform(bbox[2], bbox[3])
    # Ensure min/max ordering
    minx, maxx = min(x1, x2), max(x1, x2)
    miny, maxy = min(y1, y2), max(y1, y2)
    return minx, miny, maxx, maxy


def bbox_request_params_to_epsg25832(
    request_params: RequestParams,
) -> Optional[Tuple[float, float, float, float]]:
    """Return the request WGS84 bbox reprojected to EPSG:25832, or ``None`` if no bbox is set."""
    bbox_wgs84 = request_params.bbox_as_wgs84_tuple
    if bbox_wgs84 is None:
        return None
    return bbox_wgs84_to_epsg25832(bbox_wgs84)
