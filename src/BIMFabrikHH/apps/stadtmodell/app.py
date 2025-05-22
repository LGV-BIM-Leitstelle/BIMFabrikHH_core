from typing import List, Tuple

import numpy
from ifcopenshell.api import context, geometry, pset, root, spatial
from lxml import etree

from ...core.ifc_modelbuilder import IfcModelBuilder
from ...core.ifc_snippets import IfcSnippets
from ...core.ifc_utils import IfcFileCreator
from ...core.ogc_values_extractor import extract_project_info
from ...pydantic_models.params_tree import RequestParams
from .building_objects import Building, Point


class CityGMLParser:
    def __init__(self):
        self.ns = {
            "gml": "http://www.opengis.net/gml",
            "core": "http://www.opengis.net/citygml/1.0",
            "bldg": "http://www.opengis.net/citygml/building/1.0",
            "xAL": "urn:oasis:names:tc:ciq:xsdschema:xAL:2.0",
        }

        self.buildings = {}

    def parse_file(self, filepath: str) -> None:
        """Parse a CityGML file and extract buildings with their geometry."""
        tree = etree.parse(filepath)
        root_citygml = tree.getroot()

        # Find all buildings
        building_elements = root_citygml.xpath(".//bldg:Building", namespaces=self.ns)

        for building in building_elements:
            building_id = building.get(f"{{{self.ns['gml']}}}id")
            self.extract_building(building, building_id)

    def extract_building(self, building_element: etree.Element, building_id: str) -> None:
        """Extract geometry and properties for a single building."""
        faces = []

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
        building = Building(building_id, (vertices, face_indices)) # TODO: Type check schlägt fehlt, stimmt das sicher so?

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
        """Extract points from a polygon element."""
        face_points = []
        pos_list = polygon.xpath(".//gml:posList", namespaces=self.ns)

        if pos_list:
            coords = pos_list[0].text.split()
            try:
                for i in range(0, len(coords), 3):
                    point = Point(float(coords[i].strip()), float(coords[i + 1].strip()), float(coords[i + 2].strip()))
                    face_points.append(point)
            except (ValueError, IndexError) as e:
                print(f"Warning: Invalid coordinate data in polygon: {e}")
                return []

        return face_points

    @staticmethod
    def _convert_to_indexed_geometry(
        faces: List[List[Point]],
    ) -> Tuple[List[Tuple[float, float, float]], List[List[int]]]:
        """Convert face-vertex geometry to indexed format."""
        vertices = []
        face_indices = []
        vertex_map = {}
        vertex_index = 0

        for face in faces:
            current_face_indices = []
            for point in face:
                vertex_key = (point.x, point.y, point.z)
                if vertex_key not in vertex_map:
                    vertex_map[vertex_key] = vertex_index
                    vertices.append(vertex_key)
                    vertex_index += 1
                current_face_indices.append(vertex_map[vertex_key])
            face_indices.append(current_face_indices)

        return vertices, face_indices

    @staticmethod
    def _extract_address(address_element: etree.Element) -> str:
        """Extract formatted address from xAL address element."""
        # Implement address extraction based on your needs
        return str(etree.tostring(address_element))

    @staticmethod
    def move_element(model, element, translation_x, translation_y, translation_z=0):
        """
        Moves an element in the IFC model by the specified translation distances.

        Args:
            model: The IFC model containing the element.
            element: The element to move.
            translation_x (float): Distance to move along the X-axis.
            translation_y (float): Distance to move along the Y-axis.
            translation_z (float): Distance to move along the Z-axis (default is 0).
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


def process_gml_to_ifc(gml_files: List, model_params: RequestParams, reset_model=False, folder_path=None):
    """Process CityGML file and create IFC with separate building objects."""

    parser = CityGMLParser()
    builder = IfcModelBuilder()

    # Build project
    project_name, site_name, building_name = extract_project_info(model_params.containers)
    builder.build_project(project_name=project_name, site_name=site_name, building_name=building_name)
    model = builder.get_model()

    # builder.reset_model()

    # Create geometry representation
    model3d = context.add_context(model, context_type="Model")
    body = context.add_context(
        model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
    )

    # Reset IFC model
    if reset_model:
        builder.reset_model()
        reset_model = False

    # folder_path = Path(PathUrl.URL_UDP_CITYMODELL_LOD1)

    for file in gml_files:
        file_path = folder_path / file

        # Parse CityGML file
        parser.parse_file(str(file_path))

        # print(parser.buildings)

        # Check if there are buildings
        if not parser.buildings:
            print("No buildings found. IFC file will not be created.")
            return None

        # Create separate objects for each building
        for building_id, building in parser.buildings.items():
            # Create nested structure for the IFC geometry
            nested_vertices = [building.vertices]
            nested_faces = [building.faces]

            # Create name from building properties (GUID of the cityGML)
            building_name = f"{building.id}"
            # if building.address:
            #     building_name += f"_{building.address}"

            # Create the building in IFC
            element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=building_name)

            pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")

            pset.edit_pset(
                model,
                pset=pset_ifc,
                properties={
                    "_IDEbene1": "Gebaeude",
                    "_IDEbene2": "Gebaeude",
                    "_IDEbene3": "Gebaeude",
                    "_GebaeudeID": building.id,
                    "_GebaeudeHoehe": building.height,
                    "_AnzahlDerGeschosse": building.stories,
                    "_Postleitzahl": building.postcode,
                },
            )

            representation = geometry.add_mesh_representation(
                model, context=body, vertices=nested_vertices, faces=nested_faces, edges=None
            )

            geometry.assign_representation(model, product=element, representation=representation)

            # Assign to storey
            site_entity = model.by_type("IfcSite")[0]
            spatial.assign_container(model, relating_structure=site_entity, products=[element])

            transformation = False
            if transformation:
                # Move element with specified translations
                translation_x = -549714.19  # + 3565567.31
                translation_y = -5937004.23  # + 5928239.73
                translation_z = 0

                # Call the function
                parser.move_element(model, element, translation_x, translation_y, translation_z)

            # Analysis
            color_analysis = False
            if color_analysis:
                try:
                    if int(building.stories) > 3:
                        ifc_snippets.assign_color_to_element(model, representation, "15, 19, 218", 0.0)
                except Exception as e:
                    print(f"Fehler: {e}\n{building.id} hat keine Daten.")

    if model:
        # IfcFileCreator.save_ifc_file(model, "Hamburg_Buildings.ifc")
        # print("*" * 200)
        # print("Ifc file saved")
        # print("*" * 200)

        ifc_bytes = IfcFileCreator.save_ifc_in_memory(model)

        return ifc_bytes

    else:
        print("No models were processed; no IFC file was saved.")
