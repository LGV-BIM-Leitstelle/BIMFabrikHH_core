from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import rasterio
from ifcopenshell.api import context, geometry, pset, root, spatial
from scipy.spatial import Delaunay

from ....core.geometry.basepoint_objects import BasePointNorth
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_snippets import IfcSnippets
from ....core.ifc_utils import IfcFileCreator
from ....core.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from ....data_models.params_tree import RequestParams
from ....default_data.paths import PathConfig

ifc_snippets = IfcSnippets()


def analyze_terrain_features(elevation_data: np.ndarray) -> np.ndarray:
    """
    Detect important terrain features using gradient analysis.

    Args:
        elevation_data: 2D numpy array of elevation values

    Returns:
        2D numpy array of importance values for each point
    """
    # Handle invalid values
    elevation_data = np.nan_to_num(elevation_data, nan=0.0, posinf=None, neginf=None)

    # Calculate gradients in x and y directions
    gradient_y, gradient_x = np.gradient(elevation_data)

    # Handle any remaining invalid values in gradients
    gradient_x = np.nan_to_num(gradient_x, nan=0.0)
    gradient_y = np.nan_to_num(gradient_y, nan=0.0)

    # Calculate slope
    slope = np.sqrt(gradient_x**2 + gradient_y**2)

    # Calculate curvature (second derivative)
    curvature = np.gradient(gradient_x)[0] + np.gradient(gradient_y)[1]

    # Handle any invalid values in curvature
    curvature = np.nan_to_num(curvature, nan=0.0)

    # Combine metrics to identify important points
    # We weight slope more heavily than curvature as it's often more significant
    importance = 0.7 * slope + 0.3 * np.abs(curvature)

    return importance


def adaptive_sampling(
    elevation_data: np.ndarray, transform: np.ndarray, min_points: int = 1000, importance_threshold: float = 0.1
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Sample points adaptively based on terrain importance.

    Args:
        elevation_data: 2D numpy array of elevation values
        transform: Affine transform from rasterio
        min_points: Minimum number of points to keep
        importance_threshold: Threshold for point importance (0-1)

    Returns:
        Tuple of (x_coords, y_coords, z_values) for selected points
    """
    # Handle invalid values in elevation data first
    elevation_data = np.nan_to_num(elevation_data, nan=0.0)

    # Calculate importance of each point
    importance = analyze_terrain_features(elevation_data)

    # Normalize importance values to 0-1
    importance_range = importance.max() - importance.min()
    if importance_range > 0:
        importance = (importance - importance.min()) / importance_range
    else:
        # If all points have the same importance, create uniform grid
        importance = np.ones_like(importance)

    # Create coordinate grids in real-world coordinates
    height, width = elevation_data.shape
    x = np.linspace(transform[2], transform[2] + transform[0] * width, width)
    y = np.linspace(transform[5], transform[5] + transform[4] * height, height)
    X, Y = np.meshgrid(x, y)

    # Select points where importance > threshold
    mask = importance > importance_threshold

    # Ensure minimum number of points
    if np.sum(mask) < min_points:
        # Take top min_points by importance
        flat_importance = importance.flatten()
        threshold = np.sort(flat_importance)[-min_points]
        mask = importance > threshold

    # Extract coordinates and elevations
    x_coords = X[mask]
    y_coords = Y[mask]
    z_values = elevation_data[mask]

    return x_coords, y_coords, z_values


def generate_optimized_mesh(
    x_coords: np.ndarray, y_coords: np.ndarray, z_values: np.ndarray
) -> Tuple[List[List[float]], List[List[int]]]:
    """
    Generate an optimized mesh using Delaunay triangulation.

    Args:
        x_coords: Array of x coordinates
        y_coords: Array of y coordinates
        z_values: Array of elevation values

    Returns:
        Tuple of (vertices, faces) where vertices are [x,y,z] coordinates
        and faces are triangle indices
    """
    if len(x_coords) < 3:
        print("Not enough points for triangulation (minimum 3 required)")
        return [], []

    try:
        # Combine x,y coordinates for triangulation
        points_2d = np.column_stack((x_coords, y_coords))

        # Create Delaunay triangulation
        tri = Delaunay(points_2d)

        # Create vertices list with 3D coordinates
        vertices = np.column_stack((x_coords, y_coords, z_values)).tolist()

        # Get faces (triangle indices)
        faces = tri.simplices.tolist()

        return vertices, faces
    except Exception as e:
        print(f"Error during mesh generation: {e}")
        return [], []


def extract_optimized_mesh_data(
    input_path: str, min_points: int = 1000, importance_threshold: float = 0.1
) -> Tuple[List[List[float]], List[List[int]]]:
    """
    Extract optimized mesh data from GeoTIFF using adaptive sampling.

    Args:
        input_path: Path to the GeoTIFF file
        min_points: Minimum number of points to keep
        importance_threshold: Threshold for point importance (0-1)

    Returns:
        Tuple of (vertices, faces) for the optimized mesh
    """
    try:
        # Basic path validation
        file_path = Path(input_path)
        if not file_path.exists() or not file_path.is_file():
            print(f"Invalid file path: {input_path}")
            return [], []

        # Check file extension
        if file_path.suffix.lower() not in [".tif", ".tiff"]:
            print(f"Invalid file type: {input_path}")
            return [], []

        with rasterio.open(str(file_path)) as src:
            # Read elevation data
            elevation_data = src.read(1)

            if elevation_data.size == 0:
                print(f"Empty elevation data in file: {input_path}")
                return [], []

            # Get the transform for coordinate conversion
            transform = src.transform

            # Perform adaptive sampling
            x_coords, y_coords, z_values = adaptive_sampling(
                elevation_data, transform, min_points=min_points, importance_threshold=importance_threshold
            )

            if len(x_coords) < 3:
                print(f"Not enough valid points found in file: {input_path}")
                return [], []

            print(f"Processing {len(x_coords)} points from {input_path}")

            # Generate optimized mesh
            vertices, faces = generate_optimized_mesh(x_coords, y_coords, z_values)

            if vertices and faces:
                print(f"Generated mesh with {len(vertices)} vertices and {len(faces)} faces")

            return vertices, faces

    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return [], []


def create_terrain_ifc(
    vertices: List[List[float]], faces: List[List[int]], input_data: RequestParams
) -> Optional[bytes]:
    """
    Convert terrain mesh data to IFC format.

    Args:
        vertices: List of [x,y,z] coordinates
        faces: List of triangle indices
        input_data: Request parameters containing project info

    Returns:
        IFC file contents as bytes, or None if conversion fails
    """
    if not vertices or not faces:
        print("No valid terrain data to convert.")
        return None

    try:
        print(f"\nCreating IFC model with {len(vertices)} vertices and {len(faces)} faces...")

        # Create IFC
        builder = IfcModelBuilder()
        project_name, site_name, building_name = extract_project_info(input_data.containers)

        builder.build_project(project_name=project_name, site_name=site_name, building_name="DGM")
        model = builder.get_model()

        if not model:
            print("Failed to create IFC model")
            return None

        # Create contexts
        print("Creating IFC contexts...")
        model3d = context.add_context(model, context_type="Model")
        body = context.add_context(
            model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
        )

        # Create terrain element
        print("Creating terrain element...")
        element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name="DGM")
        if not element:
            print("Failed to create terrain element")
            return None

        spatial.assign_container(model, relating_structure=builder.site, products=[element])

        # Add property sets
        print("Adding property sets...")
        pset_ifc = pset.add_pset(model, product=element, name="Pset_DGM")
        pset.edit_pset(
            model,
            pset=pset_ifc,
            properties={
                "_ArtDGM": "TIN",
                "_Herkunft": "SDP",
                "FaceCount": len(faces),
                "VertexCount": len(vertices),
            },
        )

        pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")
        pset.edit_pset(
            model,
            pset=pset_ifc,
            properties={
                "_ArtDeckschicht": "undefiniert",
                "_Bemerkung": "undefiniert",
                "_Erzeuger": "BIMFabrikHH",
                "_IDEbene1": "DGM",
                "_IDEbene2": "DGM",
                "_IDEbene3": "DGM",
                "_Status": "Bestand",
            },
        )

        # Create and assign geometry
        print("Creating mesh representation...")
        representation = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices], faces=[faces], edges=[[]]
        )

        if not representation:
            print("Failed to create mesh representation")
            return None

        print("Assigning representation to element...")
        geometry.assign_representation(model, product=element, representation=representation)
        ifc_snippets.assign_color_to_element(model, representation, "102, 204, 0", 0.0)

        # Extract base point from terrain
        print("Creating base point...")
        x, y, _ = vertices[0]
        pset_groups = extract_psets_basepoint(input_data.containers)
        # Create basepoint data for the new interface
        basepoint_data = {"position": (x, y, 0), "size": 5.0, "psets": pset_groups}
        basepoint = BasePointNorth.from_basepoint_data(basepoint_data)
        basepoint_entity = basepoint.as_product(model, builder)
        # Assign to site (or storey as fallback)
        if builder.site:
            spatial.assign_container(model, relating_structure=builder.site, products=[basepoint_entity])
        else:
            # Create a storey as fallback
            storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
            spatial.assign_container(model, relating_structure=storey, products=[basepoint_entity])

        if model:
            print("Saving IFC model...")
            output_file = PathConfig.OUTPUT / "output_dgm_optimized.ifc"
            file_path = IfcFileCreator.save_ifc_file(model, str(output_file))
            return file_path
        else:
            print("Failed to create IFC model")
            return None

    except Exception as e:
        print(f"Error creating IFC model: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def process_terrain_folder_to_ifc(
    folder_path: Path,
    tif_files: List[str],
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    input_data: Optional[RequestParams] = None,
) -> Optional[bytes]:
    """
    Process multiple GeoTIFF files and create a combined IFC file.

    Args:
        folder_path: Path to folder containing GeoTIFF files
        tif_files: List of GeoTIFF filenames to process
        min_points: Minimum number of points to keep per file
        importance_threshold: Threshold for point importance (0-1)
        input_data: Request parameters containing project info

    Returns:
        Combined IFC file contents as bytes, or None if processing fails
    """
    combined_vertices = []
    combined_faces = []

    for file in tif_files:
        file_path = folder_path / file
        print(f"Processing {file_path}...")

        vertices, faces = extract_optimized_mesh_data(
            file_path, min_points=min_points, importance_threshold=importance_threshold
        )

        if vertices and faces:
            # Adjust face indices for combined mesh
            face_offset = len(combined_vertices)
            combined_faces.extend([[v + face_offset for v in face] for face in faces])
            combined_vertices.extend(vertices)

    print(f"Combined mesh: {len(combined_faces)} faces from {len(tif_files)} files")

    return create_terrain_ifc(vertices=combined_vertices, faces=combined_faces, input_data=input_data)
