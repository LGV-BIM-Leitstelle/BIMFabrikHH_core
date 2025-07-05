from pathlib import Path
from typing import List, Tuple

import numpy
from ifcopenshell.api import context, geometry, pset, root, spatial
from lxml import etree

from ...core.geometry.basepoint_objects import BasePointNorth
from ...core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from ...core.ifc_modelbuilder import IfcModelBuilder
from ...core.ifc_snippets import IfcSnippets
from ...core.ifc_utils import IfcFileCreator
from ...core.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from ...data_models.params_tree import RequestParams
from ...default_data.paths import PathConfig
from .building_objects import Building, Point


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
        }
        self.buildings: dict = {}

    def parse_file(self, filepath: str) -> None:
        """
        Efficiently parse a CityGML file and extract buildings with their geometry using streaming.

        Args:
            filepath (str): Path to the CityGML file.
        """
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                raise FileNotFoundError(f"CityGML file not found: {filepath}")
            if not file_path.is_file():
                raise ValueError(f"Path is not a file: {filepath}")
            # Use lxml.etree.iterparse for streaming parsing
            context = etree.iterparse(
                str(file_path), events=("end",), tag="{http://www.opengis.net/citygml/building/1.0}Building"
            )
            for event, building in context:
                building_id = building.get(f"{{{self.ns['gml']}}}id")
                if building_id:
                    self.extract_building(building, building_id)
                else:
                    print(f"Warning: Found building element without ID, skipping")
                # Free memory for processed element
                building.clear()
                while building.getprevious() is not None:
                    del building.getparent()[0]
            del context
        except etree.XMLSyntaxError as e:
            print(f"XML Syntax Error: {e}")
            raise
        except Exception as e:
            print(f"Error parsing CityGML file: {e}")
            raise

    def extract_building(self, building_element: etree.Element, building_id: str) -> None:
        """
        Extract geometry and properties for a single building.

        Args:
            building_element (etree.Element): XML element for the building.
            building_id (str): Unique building ID.
        """
        faces: List[List[Point]] = []
        # Try LOD1 geometry first
        lod1_solids = building_element.xpath(".//bldg:lod1Solid//gml:Solid", namespaces=self.ns)
        if lod1_solids:
            # Process LOD1 geometry
            for polygon in lod1_solids[0].xpath(".//gml:Polygon", namespaces=self.ns):
                face_points = self._extract_polygon_points(polygon)
                if face_points:
                    faces.append(face_points)
        else:
            # Try LOD2 geometry
            # First check if we have a direct LOD2 solid
            lod2_refs = building_element.xpath(
                ".//bldg:lod2Solid//gml:surfaceMember/@xlink:href",
                namespaces={**self.ns, "xlink": "http://www.w3.org/1999/xlink"},
            )
            if lod2_refs:
                # Process referenced geometries
                for ref in lod2_refs:
                    # Remove '#' from reference
                    ref_id = ref.lstrip("#")
                    # Find corresponding polygon
                    polygon = building_element.xpath(f".//*[@gml:id='{ref_id}']", namespaces=self.ns)
                    if polygon:
                        face_points = self._extract_polygon_points(polygon[0])
                        if face_points:
                            faces.append(face_points)
            else:
                # Try to get geometry from boundedBy surfaces
                surface_types = ["GroundSurface", "RoofSurface", "WallSurface"]
                for surface_type in surface_types:
                    surfaces = building_element.xpath(
                        f".//bldg:boundedBy/bldg:{surface_type}//gml:Polygon", namespaces=self.ns
                    )
                    for polygon in surfaces:
                        face_points = self._extract_polygon_points(polygon)
                        if face_points:
                            faces.append(face_points)
        if not faces:
            print(f"Warning: No geometry found for building {building_id}")
            return
        # Convert to vertices and face indices
        vertices, face_indices = self._convert_to_indexed_geometry(faces)
        # Create building object
        building = Building(building_id, (vertices, face_indices))
        # Extract additional properties
        height = building_element.xpath(".//bldg:measuredHeight", namespaces=self.ns)
        if height:
            try:
                building.height = float(height[0].text)
            except (ValueError, TypeError):
                print(f"Warning: Invalid height value for building {building_id}")
        stories = building_element.xpath(".//bldg:storeysAboveGround", namespaces=self.ns)
        if stories:
            try:
                building.stories = int(stories[0].text)
            except (ValueError, TypeError):
                print(f"Warning: Invalid stories value for building {building_id}")
        # Extract address
        address = building_element.xpath(".//xAL:AddressDetails", namespaces=self.ns)
        if address:
            building.address = self._extract_address(address[0])
        # Extract Postcode
        postcode = building_element.xpath(".//xAL:PostalCodeNumber", namespaces=self.ns)
        if postcode:
            building.postcode = postcode[0].text
        self.buildings[building_id] = building

    def _extract_polygon_points(self, polygon: etree.Element) -> List[Point]:
        """
        Vectorized extraction of points from a polygon element using numpy.
        """
        face_points: List[Point] = []
        pos_list = polygon.xpath(".//gml:posList", namespaces=self.ns)
        if pos_list:
            coords = pos_list[0].text.split()
            try:
                arr = numpy.array(coords, dtype=float).reshape(-1, 3)
                face_points = [Point(x, y, z) for x, y, z in arr]
            except Exception as e:
                print(f"Warning: Invalid coordinate data in polygon: {e}")
                return []
        return face_points

    @staticmethod
    def _convert_to_indexed_geometry(
        faces: List[List[Point]],
    ) -> Tuple[List[Tuple[float, float, float]], List[List[int]]]:
        """
        Convert face-vertex geometry to indexed format, with memoization for coordinate tuples.
        """
        vertices: List[Tuple[float, float, float]] = []
        face_indices: List[List[int]] = []
        vertex_map: dict = {}
        vertex_index: int = 0
        # Simple memoization cache for coordinate transformation
        coord_cache = {}
        for face in faces:
            current_face_indices: List[int] = []
            for point in face:
                vertex_key = (point.x, point.y, point.z)
                if vertex_key in coord_cache:
                    idx = coord_cache[vertex_key]
                else:
                    idx = vertex_index
                    vertex_map[vertex_key] = idx
                    vertices.append(vertex_key)
                    coord_cache[vertex_key] = idx
                    vertex_index += 1
                current_face_indices.append(idx)
            face_indices.append(current_face_indices)
        return vertices, face_indices

    @staticmethod
    def _extract_address(address_element: etree.Element) -> str:
        """
        Extract formatted address from xAL address element.

        Args:
            address_element (etree.Element): Address XML element.

        Returns:
            str: String representation of the address.
        """
        # Implement address extraction based on your needs
        return str(etree.tostring(address_element))

    @staticmethod
    def move_element(model, element, translation_x: float, translation_y: float, translation_z: float = 0) -> None:
        """
        Moves an element in the IFC model by the specified translation distances.

        Args:
            model: The IFC model containing the element.
            element: The element to move.
            translation_x (float): Distance to move along the X-axis.
            translation_y (float): Distance to move along the Y-axis.
            translation_z (float, optional): Distance to move along the Z-axis. Defaults to 0.
        """
        # Initialize the transformation matrix as an identity matrix
        element_matrix = numpy.eye(4)
        # Set the translation vector (X, Y, and Z axes)
        element_matrix[0, 3] = translation_x  # X-axis translation
        element_matrix[1, 3] = translation_y  # Y-axis translation
        element_matrix[2, 3] = translation_z  # Z-axis translation
        # Apply the transformation
        geometry.edit_object_placement(model, matrix=element_matrix, product=element)


ifc_snippets = IfcSnippets()


def process_gml_to_ifc(
    gml_files: List[str],
    model_params: RequestParams,
    reset_model: bool = False,
    folder_path: Path = None,
    move_to_origin: bool = False,
) -> Path | None:
    """
    Process CityGML files and create an IFC model with separate building objects.
    """
    import time

    parser = CityGMLParser()
    builder = IfcModelBuilder()
    # Extract and convert bounding box from request parameters (WGS84 to EPSG:25832)
    bbox_wgs84 = (model_params.bbox.min_x, model_params.bbox.min_y, model_params.bbox.max_x, model_params.bbox.max_y)
    bbox = bbox_wgs84_to_epsg25832(bbox_wgs84)
    nullpunkt_x, nullpunkt_y = bbox[0], bbox[1]
    # Build project structure
    project_name, site_name, building_name = extract_project_info(model_params.containers)
    builder.build_project(project_name=project_name, site_name=site_name, building_name=building_name)
    model = builder.get_model()
    # Create geometry contexts
    model3d = context.add_context(model, context_type="Model")
    body = context.add_context(
        model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
    )
    # Assign to storey
    site_entity = model.by_type("IfcSite")[0]
    # Reset IFC model if requested
    if reset_model:
        builder.reset_model()
        reset_model = False

    total_start = time.perf_counter()
    for file in gml_files:
        file_start = time.perf_counter()
        file_path = folder_path / file if folder_path else Path(file)
        # Parse CityGML file using streaming
        parser.buildings = {}  # Reset buildings for each file
        parse_start = time.perf_counter()
        parser.parse_file(str(file_path))
        parse_end = time.perf_counter()
        # Check if there are buildings
        if not parser.buildings:
            print("No buildings found. IFC file will not be created.")
            return None

        # --- Batching: Collect all building data first ---
        batch_collect_start = time.perf_counter()
        building_data = []
        building_debug_count = 0
        for building_id, building in parser.buildings.items():
            # Collect all unique vertex indices from all faces
            vertex_indices = set(idx for face in building.faces for idx in face)
            # Map indices to coordinates
            all_vertices = [building.vertices[idx] for idx in vertex_indices]
            if not all_vertices:
                continue  # Skip buildings with no vertices
            # Optionally shift all vertices so Nullpunkt is at (0,0)
            if move_to_origin:
                shifted_vertices = [(vx - nullpunkt_x, vy - nullpunkt_y, vz) for (vx, vy, vz) in building.vertices]
            else:
                shifted_vertices = list(building.vertices)
            # Fast inclusion: break as soon as any point is inside
            include_building = False
            for v in all_vertices:
                if bbox[0] <= v[0] <= bbox[2] and bbox[1] <= v[1] <= bbox[3]:
                    include_building = True
                    break
            if not include_building:
                continue  # Skip this building
            nested_vertices = [shifted_vertices]
            nested_faces = [building.faces]
            building_name = f"{building.id}"
            building_data.append(
                {
                    "id": building.id,
                    "name": building_name,
                    "vertices": nested_vertices,
                    "faces": nested_faces,
                    "height": building.height,
                    "stories": building.stories,
                    "postcode": building.postcode,
                }
            )
        batch_collect_end = time.perf_counter()

        # --- Batch create IFC entities ---
        batch_create_start = time.perf_counter()
        elements = [
            root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=data["name"]) for data in building_data
        ]
        batch_create_end = time.perf_counter()

        # --- Batch assign geometry, properties, and relationships ---
        batch_assign_start = time.perf_counter()
        for element, data in zip(elements, building_data):
            pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")
            pset.edit_pset(
                model,
                pset=pset_ifc,
                properties={
                    "_IDEbene1": "Gebaeude",
                    "_IDEbene2": "Gebaeude",
                    "_IDEbene3": "Gebaeude",
                    "_GebaeudeID": data["id"],
                    "_GebaeudeHoehe": data["height"],
                    "_AnzahlDerGeschosse": data["stories"],
                    "_Postleitzahl": data["postcode"],
                },
            )
            representation = geometry.add_mesh_representation(
                model, context=body, vertices=data["vertices"], faces=data["faces"], edges=None
            )
            geometry.assign_representation(model, product=element, representation=representation)
            spatial.assign_container(model, relating_structure=site_entity, products=[element])
            color_analysis = False
            if color_analysis:
                try:
                    if int(data["stories"]) > 3:
                        IfcSnippets().assign_color_to_element(model, representation, "15, 19, 218", 0.0)
                except Exception as e:
                    print(f"Fehler: {e}\n{data['id']} hat keine Daten.")
        batch_assign_end = time.perf_counter()

        file_end = time.perf_counter()
        print(f"Processed {file} in {file_end - file_start:.2f} seconds")
        print(
            f"  - Parsing: {parse_end - parse_start:.2f}s, Collect: {batch_collect_end - batch_collect_start:.2f}s, "
            f"Create: {batch_create_end - batch_create_start:.2f}s, Assign: {batch_assign_end - batch_assign_start:.2f}s"
        )
    total_end = time.perf_counter()
    print(f"Total process_gml_to_ifc time: {total_end - total_start:.2f} seconds")

    # Set base point at (0,0) if moved, else at original nullpunkt
    if move_to_origin:
        x, y = 0, 0
    else:
        x, y = nullpunkt_x, nullpunkt_y
    pset_groups = extract_psets_basepoint(model_params.containers)
    # Create basepoint data for the new interface
    basepoint_data = {"position": (x, y, 0), "size": 1.0, "psets": pset_groups}
    basepoint = BasePointNorth.from_basepoint_data(basepoint_data)
    basepoint_start = time.perf_counter()
    basepoint_entity = basepoint.as_product(model, builder)
    # Assign to site
    spatial.assign_container(model, relating_structure=site_entity, products=[basepoint_entity])
    basepoint_end = time.perf_counter()
    print(f"Base point creation: {basepoint_end - basepoint_start:.2f} seconds")
    file_write_start = time.perf_counter()
    if model:
        output_file = PathConfig.OUTPUT / "output_citymodel.ifc"
        file_path = IfcFileCreator.save_ifc_file(model, str(output_file))
        file_write_end = time.perf_counter()
        print(f"IFC file write: {file_write_end - file_write_start:.2f} seconds")
        return file_path
    else:
        print("No models were processed; no IFC file was saved.")
        return None


def is_building_in_bbox(vertices, bbox):
    """
    Check if any vertex of the building is inside the bounding box.
    vertices: list of (x, y, z) tuples or numpy array shape (N, 3)
    bbox: (minx, miny, maxx, maxy)
    """
    arr = numpy.array(vertices)
    if arr.size == 0 or arr.ndim != 2 or arr.shape[1] < 2:
        return False  # No valid vertices to check
    inside = (arr[:, 0] >= bbox[0]) & (arr[:, 0] <= bbox[2]) & (arr[:, 1] >= bbox[1]) & (arr[:, 1] <= bbox[3])
    return numpy.any(inside)


def group3(seq):
    """Group a flat list into (x, y, z) tuples."""
    return list(zip(seq[::3], seq[1::3], seq[2::3]))
