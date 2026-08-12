"""Pure data-processing helpers for city-model apps.

Reads CityGML tiles via :class:`CityGMLParser`, optionally crops by
WGS84 bbox (reprojected to EPSG:25832), and returns a list of validated
:class:`Building` records ready to be passed to
:class:`CityBasicApp.build_ifc` (or any future city record-builder).

Nothing in here touches ``ifcopenshell`` or ``ifcfactory`` — the module
is purely about turning CityGML files into a DTO list.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Sequence, Tuple, Union

from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

logger = get_logger("city_processing")


BboxWgs84 = Tuple[float, float, float, float]
BboxUtm = Tuple[float, float, float, float]


def _resolve_file_path(
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
) -> List[Building]:
    """Parse one or more CityGML tiles into a list of :class:`Building`.

    Args:
        gml_files: File names or paths of CityGML/GML/XML tiles.
        folder_path: Optional folder, URL, or mount prefix. ``None`` means
            each entry in ``gml_files`` is already a full path/URL.
        bbox_wgs84: Optional WGS84 bbox ``(min_x, min_y, max_x, max_y)``.
            When given, the bbox is reprojected to EPSG:25832 and each
            tile's parser is asked to drop buildings outside, then every
            surviving building is re-checked against the bbox (matches
            the historical ``CityModularApp.get_data_in_bbox`` behaviour).
        building_id_filter: Optional single-building gml-id filter.

    Returns:
        All buildings (across all files) whose geometry is non-empty and
        — when a bbox is given — whose vertices intersect the bbox.
    """
    bbox_epsg: Optional[BboxUtm] = None
    if bbox_wgs84 is not None:
        bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)

    parser = CityGMLParser()
    result: List[Building] = []

    for file in gml_files:
        file_path = _resolve_file_path(file, folder_path)

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


__all__ = ["parse_gml_files"]
