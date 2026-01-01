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

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.utils.geometry_utils import (
    convert_faces_with_voids_to_ifc_format,
    convert_to_indexed_geometry,
    extract_polygon_with_voids,
)
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

from .helpers import extract_attributes_from_xml

logger = get_level_logger("city_app")


# Map of mounted paths to actual file system paths
MOUNTED_PATHS = {
    "/citymodel_lod1": r"C:\_Lokale_Daten_ungesichert\__GitHubProjects\__DatenAPI_BIMFabrikHH\LoD1-DE_HH_2023-04-01",
    "/citymodel_lod2": r"C:\_Lokale_Daten_ungesichert\__GitHubProjects\__DatenAPI_BIMFabrikHH\LoD2-DE_HH_2023-04-01",
}


class CityGMLParser:
    """
    Parses CityGML files and extracts building geometry and properties for IFC conversion.
    """

    def __init__(self) -> None:
        """
        Initialize the CityGMLParser with namespace definitions and building storage.
        """
        self.ns: dict = {
            "gml": "http://www.opengis.net/gml",
            "core": "http://www.opengis.net/citygml/1.0",
            "bldg": "http://www.opengis.net/citygml/building/1.0",
            "xAL": "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0",
            "gen": "http://www.opengis.net/citygml/generics/1.0",
        }
        self.buildings: dict = {}
        self.first_building_printed = False
        # Timing statistics
        self.timing_stats = {
            "xml_parsing": 0.0,
            "attribute_extraction": 0.0,
            "geometry_extraction": 0.0,
            "pydantic_creation": 0.0,
            "total_buildings": 0,
        }

    def _get_file_source(self, filepath: str) -> Union[Path, io.BytesIO]:
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

        # Check if it's a mounted path
        if filepath.startswith("/"):
            for mount_point, real_path in MOUNTED_PATHS.items():
                if filepath.startswith(mount_point):
                    relative_path = filepath[len(mount_point) :].lstrip("/")
                    full_path = Path(real_path) / relative_path
                    if full_path.exists():
                        return full_path
                    else:
                        logger.error(f"File not found at actual path: {full_path}")
                        raise FileNotFoundError(f"CityGML file not found: {filepath} (actual path: {full_path})")
            raise FileNotFoundError(f"No matching mount point found for: {filepath}")

        # Regular file system path
        file_path = Path(filepath)
        if not file_path.exists():
            raise FileNotFoundError(f"CityGML file not found: {filepath}")
        if not file_path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        return file_path

    def parse_file(self, filepath: str, bbox_epsg: Tuple[float, float, float, float] | None = None) -> None:
        """
        Efficiently parse a CityGML file and extract buildings with their geometry using streaming.

        Args:
            filepath (str): Path to the CityGML file, mounted path, or URL.
            bbox_epsg: Optional bounding box in EPSG:25832
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
                    f"Filter bbox (UTM): min=({bbox_epsg[0]:.1f}, {bbox_epsg[1]:.1f}), max=({bbox_epsg[2]:.1f}, {bbox_epsg[3]:.1f})"
                )

            # Use lxml.etree.iterparse for streaming parsing
            # Works with both file paths (as string) and file-like objects (BytesIO)
            xml_context = etree.iterparse(
                str(file_source) if isinstance(file_source, Path) else file_source,
                events=("end",),
                tag="{http://www.opengis.net/citygml/building/1.0}Building",
            )

            building_count = 0
            pos_xpath = etree.XPath(".//gml:posList", namespaces={"gml": "http://www.opengis.net/gml"})
            for _, building in xml_context:
                # Early BBOX skip -------------------------------------------------
                if bbox_epsg:
                    minx = miny = 1e20
                    maxx = maxy = -1e20
                    for pos in pos_xpath(building):
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
                        except Exception:
                            continue

                    # Check if building bbox overlaps with the EPSG:25832 bbox
                    # Both are now in the same coordinate system (EPSG:25832)
                    if maxx < bbox_epsg[0] or maxy < bbox_epsg[1] or minx > bbox_epsg[2] or miny > bbox_epsg[3]:
                        # Skip buildings outside bbox
                        building.clear()
                        while building.getprevious() is not None:
                            del building.getparent()[0]
                        continue

                building_id = building.get(f"{{{self.ns['gml']}}}id")
                if building_id:
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

    def extract_building(self, building_element: etree.Element, building_id: str) -> None:
        """
        Extract geometry and properties for a single building.

        Args:
            building_element (etree.Element): XML element for the building.
            building_id (str): Unique building ID.
        """
        geom_start = time.perf_counter()
        faces: List[List[Tuple[float, float, float]]] = []
        faces_with_voids: List[Tuple[List[Tuple[float, float, float]], List[List[Tuple[float, float, float]]]]] = []

        # Try LOD1 geometry first
        lod1_solids = building_element.xpath(".//bldg:lod1Solid//gml:Solid", namespaces=self.ns)
        if lod1_solids:
            lod = "LoD1"
            # Process LOD1 geometry
            for polygon in lod1_solids[0].xpath(".//gml:Polygon", namespaces=self.ns):
                exterior_points, interior_points = extract_polygon_with_voids(polygon, self.ns)
                if exterior_points:
                    if interior_points:
                        # Has voids - store for special handling
                        faces_with_voids.append((exterior_points, interior_points))
                    else:
                        # No voids - use standard approach
                        faces.append(exterior_points)
        else:
            # Try LOD2 geometry
            # First check if we have a direct LOD2 solid
            lod2_refs = building_element.xpath(
                ".//bldg:lod2Solid//gml:surfaceMember/@xlink:href",
                namespaces={**self.ns, "xlink": "http://www.w3.org/1999/xlink"},
            )
            if lod2_refs:
                lod = "LoD2"
                # Process referenced geometries
                for ref in lod2_refs:
                    # Remove '#' from reference
                    ref_id = ref.lstrip("#")
                    # Find corresponding polygon
                    polygon = building_element.xpath(f".//*[@gml:id='{ref_id}']", namespaces=self.ns)
                    if polygon:
                        exterior_points, interior_points = extract_polygon_with_voids(polygon[0], self.ns)
                        if exterior_points:
                            if interior_points:
                                # Has voids - store for special handling
                                faces_with_voids.append((exterior_points, interior_points))
                            else:
                                # No voids - use standard approach
                                faces.append(exterior_points)
            else:
                lod = None
                # Try to get geometry from boundedBy surfaces
                surface_types = ["GroundSurface", "RoofSurface", "WallSurface"]
                for surface_type in surface_types:
                    surfaces = building_element.xpath(
                        f".//bldg:boundedBy/bldg:{surface_type}//gml:Polygon", namespaces=self.ns
                    )
                    for polygon in surfaces:
                        exterior_points, interior_points = extract_polygon_with_voids(polygon, self.ns)
                        if exterior_points:
                            if interior_points:
                                # Has voids - store for special handling
                                faces_with_voids.append((exterior_points, interior_points))
                            else:
                                # No voids - use standard approach
                                faces.append(exterior_points)

        geom_end = time.perf_counter()
        self.timing_stats["geometry_extraction"] += geom_end - geom_start

        if not faces and not faces_with_voids:
            logger.warning(f"Warning: No geometry found for building {building_id}")
            return

        # Create and populate attributes first
        attributes = extract_attributes_from_xml(building_element, self.ns, lod=lod, timing_stats=self.timing_stats)

        # Handle faces with voids separately
        faces_with_voids_structures = None
        if faces_with_voids:
            # Found faces with voids for building {building_id}
            # Convert all faces (both regular and voided) to IFC format together
            all_polygons_for_conversion = []

            # Add regular faces
            for face_points in faces:
                all_polygons_for_conversion.append((face_points, []))

            # Add faces with voids
            for exterior_points, interior_points in faces_with_voids:
                all_polygons_for_conversion.append((exterior_points, interior_points))

            # Convert everything to IFC format
            vertices, face_structures = convert_faces_with_voids_to_ifc_format(all_polygons_for_conversion)

            # Separate regular faces from faces with voids
            face_indices = []
            faces_with_voids_structures = []

            for face_structure in face_structures:
                if face_structure["type"] == "IfcIndexedPolygonalFaceWithVoids":
                    faces_with_voids_structures.append(face_structure)
                else:
                    # Convert 1-based indices back to 0-based for regular faces
                    face_indices.append([idx - 1 for idx in face_structure["coord_index"]])
        else:
            # No voids - use standard conversion
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
