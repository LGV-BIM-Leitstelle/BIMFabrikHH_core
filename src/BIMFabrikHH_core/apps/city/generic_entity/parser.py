"""Typed boundary-surface extraction, built on top of `CityGMLParser`.

`CityGMLParser` already handles:
- file source resolution (local / mounted / URL)
- streaming `iterparse` + bbox skip + memory cleanup
- attribute extraction

This module subclasses it and **only overrides** `extract_building` to
collect per-surface polygons (`RoofSurface`, `WallSurface`, …) instead
of merging them into one flat mesh.

It also provides `parse_typed_gml_files` — the public entry point for
parsing one or more GML tiles into a list of `TypedCityBuilding`.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Tuple, Union

from lxml import etree

from BIMFabrikHH_core.apps.city.generic_entity.models import BoundaryPolygon
from BIMFabrikHH_core.apps.city.helpers import extract_attributes_from_xml
from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.utils.geometry_utils import extract_polygon_with_voids
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import TypedCityBuilding

logger = get_logger("city_generic_entity_parser")

CitygmlProfile = Literal["2.0", "1.0"]

_NS_BY_PROFILE: Dict[str, Dict[str, str]] = {
    "2.0": {
        "gml": "http://www.opengis.net/gml/3.2",
        "core": "http://www.opengis.net/citygml/2.0",
        "bldg": "http://www.opengis.net/citygml/building/2.0",
        "gen": "http://www.opengis.net/citygml/genericity/2.0",
    },
    "1.0": {
        "gml": "http://www.opengis.net/gml",
        "core": "http://www.opengis.net/citygml/1.0",
        "bldg": "http://www.opengis.net/citygml/building/1.0",
        "gen": "http://www.opengis.net/citygml/generics/1.0",
    },
}


def _gml_id_attr(ns: Dict[str, str]) -> str:
    return f"{{{ns['gml']}}}id"


def _strip_closing_point(
    pts: List[Tuple[float, float, float]],
) -> List[Tuple[float, float, float]]:
    """Remove the GML closing vertex when it equals the first vertex."""
    if len(pts) > 1 and pts[0] == pts[-1]:
        return pts[:-1]
    return pts


def _direct_gml_name(building_el: etree.Element, ns: Dict[str, str]) -> str | None:
    """Text of the first direct `gml:name` child on the building root."""
    xpath = etree.XPath("./gml:name", namespaces=ns)
    for node in xpath(building_el):
        text = (node.text or "").strip()
        if text:
            return text
    return None


def _collect_polygons_for_surface(
    surface_elem: etree.Element,
    *,
    ns: Dict[str, str],
    surface_type: str,
    part_id: Optional[str],
    boundaries: List[BoundaryPolygon],
) -> None:
    poly_xpath = etree.XPath(".//gml:Polygon", namespaces=ns)
    for polygon in poly_xpath(surface_elem):
        exterior, interiors = extract_polygon_with_voids(polygon, ns)
        exterior = _strip_closing_point(exterior)
        if len(exterior) >= 3:
            cleaned_interiors = [
                _strip_closing_point(inner) for inner in interiors if len(_strip_closing_point(inner)) >= 3
            ]
            boundaries.append(
                BoundaryPolygon(
                    ring=exterior,
                    interior_rings=cleaned_interiors,
                    surface_type=surface_type,
                    source_part_id=part_id,
                )
            )


def extract_building_typed(
    building_el: etree.Element,
    building_id: str,
    *,
    ns: Dict[str, str],
    log_boundary_kinds: bool = False,
) -> Optional[TypedCityBuilding]:
    """Extract per-surface polygons from one `bldg:Building` element.

    Args:
        log_boundary_kinds: If `True`, log one INFO line per building with counts of
            polygons per `boundedBy` surface kind (`WallSurface`, `RoofSurface`, …).
    """
    boundaries: List[BoundaryPolygon] = []

    lod1_solid_xpath = etree.XPath(".//bldg:lod1Solid//gml:Solid", namespaces=ns)
    lod1_solids = lod1_solid_xpath(building_el)

    if lod1_solids:
        lod = "LoD1"
        poly_xpath = etree.XPath(".//gml:Polygon", namespaces=ns)
        for solid in lod1_solids:
            for polygon in poly_xpath(solid):
                exterior, interiors = extract_polygon_with_voids(polygon, ns)
                exterior = _strip_closing_point(exterior)
                if len(exterior) >= 3:
                    cleaned_interiors = [
                        _strip_closing_point(inner) for inner in interiors if len(_strip_closing_point(inner)) >= 3
                    ]
                    boundaries.append(
                        BoundaryPolygon(
                            ring=exterior,
                            interior_rings=cleaned_interiors,
                            surface_type="ClosureSurface",
                            source_part_id=None,
                        )
                    )
    else:
        lod = "LoD2"
        bounded_xpath = etree.XPath("bldg:boundedBy/*", namespaces=ns)
        part_xpath = etree.XPath(".//bldg:BuildingPart", namespaces=ns)

        components: List[Tuple[etree.Element, Optional[str]]] = [(building_el, None)]
        for part in part_xpath(building_el):
            components.append((part, part.get(_gml_id_attr(ns))))

        for component, part_id in components:
            for surf in bounded_xpath(component):
                tag = etree.QName(surf).localname
                _collect_polygons_for_surface(surf, ns=ns, surface_type=tag, part_id=part_id, boundaries=boundaries)

    if not boundaries:
        logger.warning("generic_entity: no geometry for building %s", building_id)
        return None

    if log_boundary_kinds:
        kind_counts = Counter(b.surface_type for b in boundaries)
        logger.info(
            "generic_entity building %s: boundary kinds (polygon counts) %s",
            building_id,
            dict(sorted(kind_counts.items())),
        )

    attributes = extract_attributes_from_xml(building_el, ns, lod=lod, timing_stats=None)
    return TypedCityBuilding(
        id=building_id,
        gml_name=_direct_gml_name(building_el, ns),
        lod=lod,
        attributes=attributes,
        boundaries=boundaries,
    )


class CityGMLTypedSurfaceParser(CityGMLParser):
    """Subclass of `CityGMLParser` that stores typed boundary surfaces.

    Everything is inherited:
    - `parse_file` (streaming, bbox skip, memory cleanup, logging)
    - `_get_file_source` (local / mounted / URL)
    - `_collect_polygon` and XPath helpers (unused here but available)

    Only `extract_building` is overridden to collect per-surface polygons
    instead of a merged flat mesh.
    """

    def __init__(self, *, profile: CitygmlProfile = "1.0", log_boundary_kinds: bool = False) -> None:
        super().__init__()
        self._profile = profile
        self._typed_ns = _NS_BY_PROFILE[profile]
        self._log_boundary_kinds = log_boundary_kinds
        self.typed_buildings: Dict[str, TypedCityBuilding] = {}

        # Always derive namespace-sensitive values from the active profile's NS dict.
        # The parent class hardcodes CityGML 1.0 URIs; we replace them here so
        # parse_file (inherited) streams the correct elements and reads gml:id correctly.
        self._BUILDING_TAG = f"{{{self._typed_ns['bldg']}}}Building"
        self._GML_ID_ATTR = f"{{{self._typed_ns['gml']}}}id"
        self._XPATH_POS_LIST = etree.XPath(".//gml:posList", namespaces=self._typed_ns)

    def extract_building(self, building_element: etree.Element, building_id: str) -> None:
        """Override: collect typed boundary surfaces instead of a merged mesh."""
        typed = extract_building_typed(
            building_element,
            building_id,
            ns=self._typed_ns,
            log_boundary_kinds=self._log_boundary_kinds,
        )
        if typed is not None:
            self.typed_buildings[building_id] = typed


# ---------------------------------------------------------------------------
# Public parsing entry point (was processing.py)
# ---------------------------------------------------------------------------

BboxWgs84 = Tuple[float, float, float, float]
BboxUtm = Tuple[float, float, float, float]


def _resolve_file_path(file: Union[str, Path], folder_path: Optional[Union[str, Path]]) -> str:
    if folder_path is None:
        return str(file)
    folder_str = str(folder_path)
    file_str = str(file)
    if folder_str.startswith("http://") or folder_str.startswith("https://"):
        return f"{folder_str}/{file_str}"
    if folder_str.startswith("/"):
        return file_str if file_str.startswith("/") else f"{folder_str}/{file_str}"
    return str(Path(folder_str) / file_str)


def _building_touches_bbox(tb: TypedCityBuilding, bbox_epsg: BboxUtm) -> bool:
    for b in tb.boundaries:
        for x, y, _ in b.ring:
            if bbox_epsg[0] <= x <= bbox_epsg[2] and bbox_epsg[1] <= y <= bbox_epsg[3]:
                return True
    return False


def parse_typed_gml_files(
    gml_files: Sequence[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
    building_id_filter: Optional[str] = None,
    profile: CitygmlProfile = "1.0",
    log_boundary_kinds: bool = False,
) -> List[TypedCityBuilding]:
    """Parse tiles into typed buildings (semantic boundary polygons preserved).

    Args:
        gml_files: CityGML filenames or paths.
        folder_path: Optional folder / URL / mount prefix.
        bbox_wgs84: Optional crop bbox in WGS84; reprojected to EPSG:25832 for filtering.
        building_id_filter: Optional `gml:id` of a single building.
        profile: `"1.0"` (default) matches Hamburg and Sachsen tiles (CityGML 1.0 / GML 3.1).
            Use `"2.0"` for files declaring `http://www.opengis.net/citygml/building/2.0`.
        log_boundary_kinds: Log polygon counts per boundary surface kind while parsing.

    Returns:
        One `TypedCityBuilding` per surviving `gml:id` (dict order preserved per file).
    """
    bbox_epsg: Optional[BboxUtm] = None
    if bbox_wgs84 is not None:
        bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)

    merged: List[TypedCityBuilding] = []
    seen: set[str] = set()

    for file in gml_files:
        path = _resolve_file_path(file, folder_path)
        parser = CityGMLTypedSurfaceParser(profile=profile, log_boundary_kinds=log_boundary_kinds)
        parser.parse_file(path, bbox_epsg=bbox_epsg, building_id_filter=building_id_filter)
        for bid, tb in parser.typed_buildings.items():
            if bid in seen:
                logger.warning("duplicate building id %s in typed merge — skipping duplicate", bid)
                continue
            if bbox_epsg is not None and not _building_touches_bbox(tb, bbox_epsg):
                continue
            seen.add(bid)
            merged.append(tb)

    return merged


__all__ = ["CitygmlProfile", "CityGMLTypedSurfaceParser", "extract_building_typed", "parse_typed_gml_files"]
