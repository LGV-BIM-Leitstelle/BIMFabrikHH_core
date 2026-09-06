"""
CityGML Parser Module

Copyright (C) 2025 Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung
BIM-Leitstelle, Ahmed Salem <ahmed.salem@gv.hamburg.de>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

import io
import time
from pathlib import Path
from typing import List, Tuple, Union

import numpy
import requests
from lxml import etree

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.utils.geometry_utils import (
    convert_faces_with_voids_to_ifc_format,
    convert_to_indexed_geometry,
    extract_polygon_with_voids,
)
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

from .helpers import extract_attributes_from_xml

logger = get_logger("city_app")

Faces = List[List[Tuple[float, float, float]]]
FacesWithVoids = List[Tuple[List[Tuple[float, float, float]], List[List[Tuple[float, float, float]]]]]


class CityGMLParser:
    """
    Parses CityGML files and extracts building geometry and properties for IFC conversion.
    """

    _NS = {
        "gml": "http://www.opengis.net/gml",
        "core": "http://www.opengis.net/citygml/1.0",
        "bldg": "http://www.opengis.net/citygml/building/1.0",
        "xAL": "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0",
        "gen": "http://www.opengis.net/citygml/generics/1.0",
    }
    _XLINK_NS = {**_NS, "xlink": "http://www.w3.org/1999/xlink"}

    _BUILDING_TAG = "{http://www.opengis.net/citygml/building/1.0}Building"
    _GML_ID_ATTR = "{http://www.opengis.net/gml}id"

    _XPATH_POS_LIST = etree.XPath(".//gml:posList", namespaces=_NS)
    _XPATH_BOUNDED_POLYS = etree.XPath("bldg:boundedBy//gml:Polygon", namespaces=_NS)
    _XPATH_LOD2_REFS = etree.XPath("bldg:lod2Solid//gml:surfaceMember/@xlink:href", namespaces=_XLINK_NS)
    _XPATH_BY_ID = etree.XPath(".//*[@gml:id=$ref_id]", namespaces=_NS)
    _XPATH_LOD1_SOLID = etree.XPath(".//bldg:lod1Solid//gml:Solid", namespaces=_NS)
    _XPATH_ALL_POLYGONS = etree.XPath(".//gml:Polygon", namespaces=_NS)
    _XPATH_BUILDING_PARTS = etree.XPath(".//bldg:BuildingPart", namespaces=_NS)

    def __init__(self) -> None:
        self.buildings: dict = {}
        self.timing_stats = {
            "xml_parsing": 0.0,
            "attribute_extraction": 0.0,
            "geometry_extraction": 0.0,
            "pydantic_creation": 0.0,
            "total_buildings": 0,
        }

    @staticmethod
    def _get_file_source(filepath: str) -> Union[Path, io.BytesIO]:
        """
        Get file source - either a local Path or BytesIO from URL.

        Args:
            filepath (str): Path to the file (local, mounted, or URL)

        Returns:
            Union[Path, io.BytesIO]: Local file path or BytesIO with URL content

        Raises:
            FileNotFoundError: If file cannot be found
        """
        # Check if it's a URL
        if filepath.startswith("http://") or filepath.startswith("https://"):
            logger.info(f"Fetching XML from URL: {filepath}")
            try:
                response = requests.get(filepath, timeout=60)
                response.raise_for_status()
                return io.BytesIO(response.content)
            except requests.RequestException as e:
                raise FileNotFoundError(f"Failed to fetch CityGML from URL: {filepath} - {e}")

        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"CityGML file not found: {filepath}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        return file_path

    def parse_file(
        self,
        filepath: str,
        bbox_epsg: Tuple[float, float, float, float] | None = None,
        building_id_filter: str | None = None,
    ) -> None:
        """
        Efficiently parse a CityGML file and extract buildings with their geometry using streaming.

        Args:
            filepath (str): Path to the CityGML file, mounted path, or URL.
            bbox_epsg: Optional bounding box in EPSG:25832
            building_id_filter: If given, only this building ID is extracted; all others are skipped
                                 before any geometry processing, making single-building runs fast.
        """
        try:
            xml_start = time.perf_counter()

            # Get file source (Path or BytesIO)
            file_source = self._get_file_source(filepath)

            # Log the source type
            if isinstance(file_source, io.BytesIO):
                logger.info(f"Parsing XML from URL: {filepath}")
            else:
                logger.info(f"Reading file from: {file_source}")

            # Log filter bbox for debugging
            if bbox_epsg:
                logger.info(
                    f"Filter bbox (UTM): "
                    f"min=({bbox_epsg[0]:.1f}, {bbox_epsg[1]:.1f}), "
                    f"max=({bbox_epsg[2]:.1f}, {bbox_epsg[3]:.1f})"
                )

            # Use lxml.etree.iterparse for streaming parsing
            # Works with both file paths (as string) and file-like objects (BytesIO)
            xml_context = etree.iterparse(
                str(file_source) if isinstance(file_source, Path) else file_source,
                events=("end",),
                tag=self._BUILDING_TAG,
            )

            building_count = 0
            for _, building in xml_context:
                # Early BBOX skip -------------------------------------------------
                if bbox_epsg:
                    minx = miny = 1e20
                    maxx = maxy = -1e20
                    for pos in self._XPATH_POS_LIST(building):
                        try:
                            arr = numpy.fromstring(pos.text.strip(), sep=" ", dtype=numpy.float64)
                            if arr.size % 3 == 0:
                                arr = arr.reshape(-1, 3)
                                xs = arr[:, 0]
                                ys = arr[:, 1]
                                minx = min(minx, xs.min())
                                miny = min(miny, ys.min())
                                maxx = max(maxx, xs.max())
                                maxy = max(maxy, ys.max())
                        except (ValueError, AttributeError):
                            continue

                    # Check if building bbox overlaps with the EPSG:25832 bbox
                    # Both are now in the same coordinate system (EPSG:25832)
                    if maxx < bbox_epsg[0] or maxy < bbox_epsg[1] or minx > bbox_epsg[2] or miny > bbox_epsg[3]:
                        # Skip buildings outside bbox
                        building.clear()
                        while building.getprevious() is not None:
                            del building.getparent()[0]
                        continue

                building_id = building.get(self._GML_ID_ATTR)
                if building_id:
                    if building_id_filter is None or building_id == building_id_filter:
                        self.extract_building(building, building_id)
                        building_count += 1
                else:
                    logger.warning("Found building element without ID, skipping")
                # Free memory for processed element
                building.clear()
                while building.getprevious() is not None:
                    del building.getparent()[0]
            del xml_context

            xml_end = time.perf_counter()
            self.timing_stats["xml_parsing"] = xml_end - xml_start
            self.timing_stats["total_buildings"] = building_count

            logger.info(
                f"XML parsing completed: {self.timing_stats['xml_parsing']:.3f}s for {building_count} buildings"
            )
            logger.info(f"  - Attribute extraction: {self.timing_stats['attribute_extraction']:.3f}s")
            logger.info(f"  - Geometry extraction: {self.timing_stats['geometry_extraction']:.3f}s")
            logger.info(f"  - Pydantic creation: {self.timing_stats['pydantic_creation']:.3f}s")

        except etree.XMLSyntaxError as e:
            logger.error(f"XML Syntax Error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error parsing CityGML file: {e}")
            raise

    def _collect_polygon(self, polygon_elem: etree.Element, faces: Faces, faces_with_voids: FacesWithVoids) -> None:
        exterior_points, interior_points = extract_polygon_with_voids(polygon_elem, self._NS)
        if exterior_points:
            if interior_points:
                faces_with_voids.append((exterior_points, interior_points))
            else:
                faces.append(exterior_points)

    def _extract_component(
        self,
        component: etree.Element,
        building_element: etree.Element,
        faces: Faces,
        faces_with_voids: FacesWithVoids,
    ) -> None:
        """Extract all LOD2 faces from one component (building or BuildingPart).

        Prefer bldg:boundedBy as it contains the complete polygon set including
        ClosureSurface elements. Fall back to lod2Solid xlink resolution only when
        no boundedBy surfaces are present.
        """
        bounded_polys = self._XPATH_BOUNDED_POLYS(component)
        if bounded_polys:
            for polygon in bounded_polys:
                self._collect_polygon(polygon, faces, faces_with_voids)
        else:
            for ref in self._XPATH_LOD2_REFS(component):
                ref_id = ref.lstrip("#")
                polygon = self._XPATH_BY_ID(component, ref_id=ref_id) or self._XPATH_BY_ID(
                    building_element, ref_id=ref_id
                )
                if polygon:
                    self._collect_polygon(polygon[0], faces, faces_with_voids)

    def extract_building(self, building_element: etree.Element, building_id: str) -> None:
        """
        Extract geometry and properties for a single building.

        Args:
            building_element (etree.Element): XML element for the building.
            building_id (str): Unique building ID.
        """
        geom_start = time.perf_counter()
        faces: Faces = []
        faces_with_voids: FacesWithVoids = []

        # Try LOD1 geometry first
        lod1_solids = self._XPATH_LOD1_SOLID(building_element)
        if lod1_solids:
            lod = "LoD1"
            for solid in lod1_solids:
                for polygon in self._XPATH_ALL_POLYGONS(solid):
                    self._collect_polygon(polygon, faces, faces_with_voids)
        else:
            lod = "LoD2"
            # Process the top-level building and each BuildingPart independently so that
            # parts with only boundedBy surfaces (no lod2Solid) are not silently skipped.
            components = [building_element] + self._XPATH_BUILDING_PARTS(building_element)
            for component in components:
                self._extract_component(component, building_element, faces, faces_with_voids)

        geom_end = time.perf_counter()
        self.timing_stats["geometry_extraction"] += geom_end - geom_start

        if not faces and not faces_with_voids:
            logger.warning(f"Warning: No geometry found for building {building_id}")
            return

        # Create and populate attributes first
        attributes = extract_attributes_from_xml(building_element, self._NS, lod=lod, timing_stats=self.timing_stats)

        # Handle faces with voids separately
        if faces_with_voids:
            all_polys = [(f, []) for f in faces] + list(faces_with_voids)
            vertices, face_structures = convert_faces_with_voids_to_ifc_format(all_polys)
            face_indices = [
                list(fs["coord_index"])
                for fs in face_structures
                if fs["type"] != "IfcIndexedPolygonalFaceWithVoids"
            ]
            faces_with_voids_structures = [
                fs for fs in face_structures if fs["type"] == "IfcIndexedPolygonalFaceWithVoids"
            ] or None
        else:
            vertices, face_indices = convert_to_indexed_geometry(faces)
            faces_with_voids_structures = None

        # create the Building with the attributes
        pydantic_start = time.perf_counter()
        building = Building(
            id=building_id,
            attributes=attributes,
            vertices=vertices,
            faces=face_indices,
            faces_with_voids=faces_with_voids_structures,
        )
        pydantic_end = time.perf_counter()
        self.timing_stats["pydantic_creation"] += pydantic_end - pydantic_start

        self.buildings[building_id] = building
