"""Modular city app implementation."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ifcfactory import BIMFactoryElement, Transform
from ifcopenshell.api import context, geometry, pset, root, spatial

from BIMFabrikHH_core.apps.city.parser import CityGMLParser
from BIMFabrikHH_core.apps.interface import UIAppInterface
from BIMFabrikHH_core.core.geometry.advanced_objects import create_basepoint_quad
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mesh_representation_with_voids(model, context, vertices, faces_with_voids):
    """Copy CityGML tessellated surfaces directly into an IfcPolygonalFaceSet."""

    # 1. Cartesian point list (XYZ tuples)
    coord_list = [tuple(map(float, v)) for v in vertices]
    point_list = model.create_entity("IfcCartesianPointList3D", CoordList=coord_list)

    # 2. Convert every supplied face exactly as-is
    ifc_faces = []
    for fs in faces_with_voids:
        outer = fs["coord_index"]  # already 1-based
        inners = fs.get("inner_coord_indices", [])

        if inners:
            ifc_faces.append(
                model.create_entity(
                    "IfcIndexedPolygonalFaceWithVoids",
                    CoordIndex=outer,
                    InnerCoordIndices=inners,
                )
            )
        else:
            ifc_faces.append(
                model.create_entity(
                    "IfcIndexedPolygonalFace",
                    CoordIndex=outer,
                )
            )

    # 3. Assemble closed face-set (the source shell is already watertight)
    face_set = model.create_entity(
        "IfcPolygonalFaceSet",
        Coordinates=point_list,
        Faces=ifc_faces,
        Closed=True,
    )

    # 4. Wrap in shape representation and return
    return model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=[face_set],
    )


# ---------------------------------------------------------------------
# Helper that IGNORES voids and returns a solid block (courtyards filled)
# ---------------------------------------------------------------------


def create_solid_representation(model, context, vertices, faces_with_voids):
    """Create a plain solid by discarding inner rings (no courtyards)."""

    # 1. Cartesian points
    coord_list = [tuple(map(float, v)) for v in vertices]
    point_list = model.create_entity("IfcCartesianPointList3D", CoordList=coord_list)

    # 2. pick outer ring of first face as footprint
    outer_ring = list(faces_with_voids[0]["coord_index"])  # 1-based

    # Build mapping from each vertex id to the lowest Z at that XY
    scale = 1_000_000  # 1e-6 precision
    xy_map: Dict[Tuple[int, int], List[Tuple[float, int]]] = {}
    for vidx, (x, y, z) in enumerate(coord_list, start=1):
        key = (int(x * scale), int(y * scale))
        xy_map.setdefault(key, []).append((z, vidx))

    top2bottom = {}
    for lst in xy_map.values():
        lst_sorted = sorted(lst)  # ascending z
        bottom_vid = lst_sorted[0][1]
        for _z, vid in lst_sorted:
            top2bottom[vid] = bottom_vid

    ifc_faces = []

    def add(indices):
        if len({coord_list[i - 1] for i in indices}) >= 3:
            ifc_faces.append(model.create_entity("IfcIndexedPolygonalFace", CoordIndex=indices))

    # top
    add(outer_ring)

    # bottom
    bottom = [top2bottom[i] for i in reversed(outer_ring)]
    add(bottom)

    # walls
    for a, b in zip(outer_ring, outer_ring[1:] + outer_ring[:1]):
        a_bot = top2bottom[a]
        b_bot = top2bottom[b]
        add([a, b, b_bot, a_bot])

    face_set = model.create_entity(
        "IfcPolygonalFaceSet",
        Coordinates=point_list,
        Faces=ifc_faces,
        Closed=True,
    )

    return model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=[face_set],
    )


# ---------------------------------------------------------------------

# Build representation using all regular faces and faces with voids (true LoD2)


def create_combined_representation(model, context, vertices, faces, faces_with_voids):
    """Create polygonal face set containing regular faces and void faces."""
    coord_list = [tuple(map(float, v)) for v in vertices]
    pt_list = model.create_entity("IfcCartesianPointList3D", CoordList=coord_list)

    ifc_faces = []

    # regular faces (0-based indices list of lists)
    if faces:
        for ring in faces:
            if len(ring) >= 3:
                # convert to 1-based
                ifc_faces.append(model.create_entity("IfcIndexedPolygonalFace", CoordIndex=[i + 1 for i in ring]))

    # faces with voids (already 1-based dicts from parser)
    if faces_with_voids:
        for fs in faces_with_voids:
            if fs["type"] == "IfcIndexedPolygonalFaceWithVoids":
                ifc_faces.append(
                    model.create_entity(
                        "IfcIndexedPolygonalFaceWithVoids",
                        CoordIndex=fs["coord_index"],
                        InnerCoordIndices=fs["inner_coord_indices"],
                    )
                )
            else:
                ifc_faces.append(
                    model.create_entity(
                        "IfcIndexedPolygonalFace",
                        CoordIndex=fs["coord_index"],
                    )
                )

    face_set = model.create_entity(
        "IfcPolygonalFaceSet",
        Coordinates=pt_list,
        Faces=ifc_faces,
        Closed=True,
    )

    return model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=[face_set],
    )


class CityModularApp(UIAppInterface):
    """Modular implementation for processing city models."""

    def __init__(self, gml_files: List[str], folder_path: Optional[Union[Path, str]] = None):
        """Initialize with GML files to process."""
        self.gml_files = gml_files
        self.folder_path = folder_path if isinstance(folder_path, str) else str(folder_path) if folder_path else None
        self.parser = CityGMLParser()

    def get_data_in_bbox(self, bbox: BoundingBoxParams) -> List[Dict[str, Any]]:
        """Step 1: Get raw data within bounding box."""

        # Convert bbox from WGS84 to EPSG:25832
        bbox_wgs84 = (bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)
        bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)
        nullpunkt_x, nullpunkt_y = bbox_epsg[0], bbox_epsg[1]

        all_building_data = []
        for file in self.gml_files:
            # Handle URLs, mounted paths, and regular paths
            if self.folder_path:
                if self.folder_path.startswith("http://") or self.folder_path.startswith("https://"):
                    # URL - use string concatenation
                    file_path = f"{self.folder_path}/{file}"
                elif self.folder_path.startswith("/"):
                    # Mounted path - use string concatenation
                    file_path = f"{self.folder_path}/{file}" if not file.startswith("/") else file
                else:
                    # Regular local path - use pathlib
                    file_path = str(Path(self.folder_path) / file)
            else:
                file_path = file

            self.parser.buildings = {}  # Reset buildings for each file
            self.parser.parse_file(file_path, bbox_epsg=bbox_epsg)

            # Debug: Count total buildings before filtering
            total_buildings_before_filter = len(self.parser.buildings)
            buildings_after_filter = 0

            for building_id, building in self.parser.buildings.items():
                vertex_indices = set(idx for face in building.faces for idx in face)
                all_vertices = [building.vertices[idx] for idx in vertex_indices]

                if not all_vertices:
                    continue

                # Check if building is in bbox
                include_building = any(
                    bbox_epsg[0] <= v[0] <= bbox_epsg[2] and bbox_epsg[1] <= v[1] <= bbox_epsg[3] for v in all_vertices
                )

                if not include_building:
                    continue

                buildings_after_filter += 1

                building_data = {
                    "id": building.id,
                    "vertices": building.vertices,
                    "faces": building.faces,
                    "attributes": building.attributes,
                }

                # Add faces with voids if available
                if hasattr(building, "faces_with_voids") and building.faces_with_voids:
                    building_data["faces_with_voids"] = building.faces_with_voids
                all_building_data.append(building_data)

        return all_building_data

    def process_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 2: Process and clean data."""

        processed_data = []
        for building in raw_data:
            try:
                # Extract vertices and faces
                vertex_indices = set(idx for face in building["faces"] for idx in face)
                all_vertices = [building["vertices"][idx] for idx in vertex_indices]

                if not all_vertices:
                    continue

                # Create processed building data
                processed_building = {
                    "id": building["id"],
                    "name": f"{building['id']}",
                    "vertices": building["vertices"],
                    "faces": building["faces"],
                    "attributes": building.get("attributes", {}),
                }

                # Add faces with voids if available
                if building.get("faces_with_voids"):
                    processed_building["faces_with_voids"] = building["faces_with_voids"]
                processed_data.append(processed_building)

            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Failed to process building: {e}")
                continue

        return processed_data

    def create_ifc(
        self, processed_data: List[Dict[str, Any]], request_params: RequestParams, output_path: Optional[Path] = None
    ) -> Path:
        """
        Step 3: Create IFC using existing RequestParams model.

        Args:
            processed_data: List of processed building data.
            request_params: Request parameters for the model.
            output_path: Optional full path where to save the IFC file.
                If None, saves to default location with default filename.

        Returns:
            Path to the saved IFC file.
        """
        if output_path is None:
            output_path = Path("output_citymodel_modular.ifc")

        try:
            # Create IFC model
            model_builder = IfcModelBuilder()

            # Extract project info from containers
            project_name, site_name, building_name = extract_project_info(request_params.containers)

            # Build project structure
            model_builder.build_project(
                project_name=project_name,
                coordinate_system=CoordinateSystemTemplates.epsg_25832(),
                coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
                site_name=site_name,
                building_name=building_name,
            )

            # Get model and contexts
            model = model_builder.model
            model3d = context.add_context(model, context_type="Model")
            body = context.add_context(
                model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
            )

            # Create building elements
            elements = [
                root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=data["name"])
                for data in processed_data
            ]

            # Add buildings to model
            color_city_model = (1.0, 1.0, 0.498)
            for element, building_data in zip(elements, processed_data):
                # Add property sets
                pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")
                pydantic_properties = building_data["attributes"].to_dict_with_labels(by_alias=True)
                properties = {k: v for k, v in pydantic_properties.items() if v is not None}
                pset.edit_pset(model, pset=pset_ifc, properties=properties)

                # Add Pset_Hyperlink (using default values)
                pset_hyperlink = pset.add_pset(model, product=element, name="Pset_Hyperlink")
                default_hyperlink = Pset_Hyperlink(
                    hyperlink_001="www.bim.hamburg.de", hyperlink_001_bemerkung="Link zur Homepage von BIM.Hamburg"
                )
                pset.edit_pset(model, pset=pset_hyperlink, properties=default_hyperlink.model_dump(by_alias=True))

                # Add geometry
                if building_data.get("faces_with_voids"):
                    # Create full LoD2 representation using walls + void faces
                    representation = create_combined_representation(
                        model,
                        context=body,
                        vertices=building_data["vertices"],
                        faces=building_data["faces"],
                        faces_with_voids=building_data["faces_with_voids"],
                    )
                else:
                    # Standard mesh representation
                    vertices = building_data["vertices"]
                    faces = building_data["faces"]
                    logger.debug(f"Building {building_data['id']}: vertices={len(vertices)}, faces={len(faces)}")
                    if len(vertices) > 0:
                        logger.debug(f"First vertex type: {type(vertices[0])}")
                    if len(faces) > 0:
                        logger.debug(
                            f"First face type: {type(faces[0])}, "
                            f"length: {len(faces[0]) if hasattr(faces[0], '__len__') else 'N/A'}"
                        )
                    # Wrap vertices and faces in outer lists to match IfcOpenShell API expectations
                    vertices_wrapped = [vertices]
                    faces_wrapped = [faces]
                    representation = geometry.add_mesh_representation(
                        model, context=body, vertices=vertices_wrapped, faces=faces_wrapped, edges=[[]]
                    )

                # Add color and layer
                IfcSnippets.assign_color_to_representation(model, representation, color_city_model, 0.0)
                IfcSnippets.assign_layer_to_representation(model, representation, "_BIM_Stadtmodell", color_city_model)

                # Assign representation and container
                geometry.assign_representation(model, product=element, representation=representation)
                spatial.assign_container(model, relating_structure=model_builder.building, products=[element])

            # Create basepoint at lower left corner of the INPUT bounding box (matching tree and DGM apps)
            if processed_data:
                # Convert bbox from WGS84 to EPSG:25832
                bbox_wgs84 = (
                    request_params.bbox.min_x,
                    request_params.bbox.min_y,
                    request_params.bbox.max_x,
                    request_params.bbox.max_y,
                )
                bbox_epsg = bbox_wgs84_to_epsg25832(bbox_wgs84)
                min_x, min_y = bbox_epsg[0], bbox_epsg[1]

                # Create basepoint using BIMFactoryElement
                basepoint_entity = BIMFactoryElement(
                    type="IfcBuildingElementProxy",
                    name="Nullpunktobjekt",
                    children=[
                        Transform(
                            vec=(min_x, min_y, 0),
                            item=create_basepoint_quad(size=8.0, psets=[]),
                        ),
                    ],
                ).build(model)

                # Assign basepoint to site
                spatial.assign_container(model, relating_structure=model_builder.site, products=[basepoint_entity])

            # Save model
            saved_path = model_builder.save_ifc_to_path(output_path)
            if not saved_path:
                raise RuntimeError("Failed to save IFC file")

            return saved_path

        except Exception as e:
            logger.error(f"Failed to create IFC: {e}")
            raise RuntimeError(f"Failed to create IFC: {e}")
