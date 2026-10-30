"""Pure data-processing helpers for city-model apps.

Reads CityGML tiles via :class:`CityGMLParser`, optionally crops by
WGS84 bbox (reprojected to the CRS of the tiles), and returns a list of validated
:class:`Building` records ready to be passed to
:class:`CityBasicApp.build_ifc` (or any future city record-builder).

Nothing in here touches ``ifcopenshell`` or ``ifcfactory`` — the module
is purely about turning CityGML files into a DTO list.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from bimfabrikhh_core_rs import declared_crs

from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing.coordinate_transformer import CoordinateTransformer
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import BboxWgs84, compound_vertical_epsg, horizontal_crs
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

logger = get_logger("city_processing")


BboxUtm = Tuple[float, float, float, float]
DeclaredCrs = Tuple[Optional[int], Optional[int]]


def resolve_file_path(
    file: Union[str, Path],
    folder_path: Optional[Union[str, Path]],
) -> str:
    """Combine ``folder_path`` + ``file`` for URLs, mounted paths and local paths.

    Replicates the dispatch logic that used to live in
    ``CityModularApp.get_data_in_bbox``:

    * If ``folder_path`` is ``None`` — use ``file`` verbatim.
    * If ``folder_path`` is an ``http(s)`` URL — join with ``/``.
    * If ``folder_path`` starts with ``/`` — treat as mounted, join with ``/``
      unless ``file`` is already absolute.
    * Otherwise — join via :class:`pathlib.Path`.
    """
    if folder_path is None:
        return str(file)

    folder_str = str(folder_path)
    file_str = str(file)

    if folder_str.startswith("http://") or folder_str.startswith("https://"):
        return f"{folder_str}/{file_str}"
    if folder_str.startswith("/"):
        return file_str if file_str.startswith("/") else f"{folder_str}/{file_str}"
    return str(Path(folder_str) / file_str)


def citygml_crs(path: Union[str, Path]) -> DeclaredCrs:
    """``(horizontal, vertical)`` EPSG codes of the first ``srsName`` of a local CityGML file.

    The name is read by :func:`bimfabrikhh_core_rs.declared_crs` (the same check
    ``gml_to_ifc`` does). A single code is resolved with pyproj, so any compound
    code (``EPSG:5555``) gives its vertical part and unknown codes give
    ``(None, None)``. ``(None, None)`` as well for remote paths and files without
    a ``srsName``.
    """
    file = Path(path)
    if not file.is_file():
        return None, None
    declared = declared_crs(str(file))
    if declared is None:
        return None, None
    horizontal, vertical = declared["horizontal_epsg"], declared["vertical_epsg"]
    if horizontal is None or vertical is not None:
        return horizontal, vertical
    try:
        return horizontal_crs(horizontal).to_epsg(), compound_vertical_epsg(horizontal)
    except ValueError:
        return None, None


def with_tile_crs(request_params: RequestParams, paths: Sequence[Union[str, Path]]) -> RequestParams:
    """``request_params`` with ``source_epsg`` / ``vertical_epsg`` taken from the tiles where empty.

    The tiles declare their CRS in ``srsName`` (see :func:`citygml_crs`);
    tiles that declare none are not checked.

    Raises:
        ValueError: The tiles declare different CRS, or a declared CRS
            contradicts ``source_epsg`` / ``vertical_epsg`` of the request.
    """
    declared = {citygml_crs(path) for path in paths} - {(None, None)}
    if not declared:
        return request_params
    if len(declared) > 1:
        raise ValueError(f"The city tiles declare different CRS (horizontal, vertical EPSG): {sorted(declared, key=str)}")
    ((horizontal, vertical),) = declared
    source = request_params.source_epsg
    if source is not None and horizontal is not None and horizontal_crs(source).to_epsg() != horizontal:
        raise ValueError(f"source_epsg EPSG:{source} contradicts the city tiles, which are in EPSG:{horizontal}")
    known_vertical = request_params.vertical_epsg
    if known_vertical is None and source is not None:
        known_vertical = compound_vertical_epsg(source)
    if known_vertical is not None and vertical is not None and known_vertical != vertical:
        raise ValueError(f"vertical_epsg EPSG:{known_vertical} contradicts the city tiles, whose heights are EPSG:{vertical}")
    update = {}
    if source is None and horizontal is not None:
        update["source_epsg"] = source = horizontal
    if known_vertical is None and vertical is not None and source is not None:
        update["vertical_epsg"] = vertical
    return request_params.model_copy(update=update) if update else request_params


def bbox_in_source_crs(bbox_wgs84: Optional[BboxWgs84], source_epsg: Optional[int]) -> Optional[BboxUtm]:
    """``bbox_wgs84`` as ``(min_x, min_y, max_x, max_y)`` in the horizontal CRS of the tiles.

    ``None`` without a bbox.

    Raises:
        ValueError: A bbox without ``source_epsg``; the tiles cannot be cropped
            in an unknown CRS.
    """
    if bbox_wgs84 is None:
        return None
    if source_epsg is None:
        raise ValueError("A bbox needs source_epsg (the CRS of the city tiles) to crop them")
    xs, ys = CoordinateTransformer(horizontal_crs(4326), horizontal_crs(source_epsg)).transform_xy_batch(
        [bbox_wgs84[0], bbox_wgs84[2]], [bbox_wgs84[1], bbox_wgs84[3]]
    )
    return min(xs), min(ys), max(xs), max(ys)


def transform_buildings(buildings: Sequence[Building], transformer: Optional[CoordinateTransformer]) -> List[Building]:
    """Copies of ``buildings`` with vertex XY transformed in one batch; Z unchanged.

    ``None`` or an identity transformer keep the buildings as they are.
    """
    if transformer is None or transformer.is_identity:
        return list(buildings)
    points = [v for b in buildings for v in b.vertices]
    xs, ys = transformer.transform_xy_batch([p[0] for p in points], [p[1] for p in points])
    moved = iter(zip(xs, ys, (p[2] for p in points)))
    return [b.model_copy(update={"vertices": [next(moved) for _ in b.vertices]}) for b in buildings]


def _building_overlaps_bbox(building: Building, bbox_epsg: BboxUtm) -> bool:
    """True if any referenced vertex of ``building`` sits inside ``bbox_epsg``."""
    vertex_indices = {idx for face in building.faces for idx in face}
    for idx in vertex_indices:
        x, y, _ = building.vertices[idx]
        if bbox_epsg[0] <= x <= bbox_epsg[2] and bbox_epsg[1] <= y <= bbox_epsg[3]:
            return True
    return False


def parse_gml_files(
    gml_files: Sequence[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    building_id_filter: Optional[str] = None,
    source_epsg: Optional[int] = 25832,
) -> List[Building]:
    """Parse one or more CityGML tiles into a list of :class:`Building`.

    Args:
        gml_files: File names or paths of CityGML/GML/XML tiles.
        folder_path: Optional folder, URL, or mount prefix. ``None`` means
            each entry in ``gml_files`` is already a full path/URL.
        bbox_wgs84: Optional WGS84 bbox ``(min_x, min_y, max_x, max_y)``.
            When given, the bbox is reprojected to ``source_epsg`` and each
            tile's parser is asked to drop buildings outside, then every
            surviving building is re-checked against the bbox (matches
            the historical ``CityModularApp.get_data_in_bbox`` behaviour).
        building_id_filter: Optional single-building gml-id filter.
        source_epsg: CRS of the tiles, used to crop by ``bbox_wgs84``
            (see :func:`bbox_in_source_crs`). Coordinates are not transformed.

    Returns:
        All buildings (across all files) whose geometry is non-empty and
        — when a bbox is given — whose vertices intersect the bbox.
    """
    bbox_epsg = bbox_in_source_crs(bbox_wgs84, source_epsg)

    parser = CityGMLParser()
    result: List[Building] = []

    for file in gml_files:
        file_path = resolve_file_path(file, folder_path)

        parser.buildings = {}
        parser.parse_file(
            file_path,
            bbox_epsg=bbox_epsg,
            building_id_filter=building_id_filter,
        )

        for building in parser.buildings.values():
            if not building.vertices or not building.faces:
                continue
            if bbox_epsg is not None and not _building_overlaps_bbox(building, bbox_epsg):
                continue
            result.append(building)

    logger.info("Parsed %d building(s) from %d file(s)", len(result), len(gml_files))
    return result


__all__ = [
    "bbox_in_source_crs",
    "citygml_crs",
    "parse_gml_files",
    "resolve_file_path",
    "transform_buildings",
    "with_tile_crs",
]
