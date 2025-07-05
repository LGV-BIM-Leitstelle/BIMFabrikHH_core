from pathlib import Path
from typing import List, Tuple

import numpy as np
import pyvista as pv
import rasterio
from ifcopenshell.api import context, geometry, pset, root, spatial
from rasterio.enums import Resampling

from ....core.geometry.basepoint_objects import BasePointNorth
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_snippets import IfcSnippets
from ....core.ifc_utils import IfcFileCreator
from ....core.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from ....data_models.params_tree import RequestParams
from ....default_data.paths import PathConfig

ifc_snippets = IfcSnippets()


def preprocess_elevation_data(elevation_data: np.ndarray) -> np.ndarray:
    """
    Fast preprocessing of elevation data with minimal operations.

    Args:
        elevation_data (np.ndarray): Raw elevation data from rasterio.

    Returns:
        np.ndarray: Processed elevation data ready for mesh generation.
    """
    # Convert to float32 for memory efficiency
    data = elevation_data.astype(np.float32)

    # Replace invalid values (NaN, inf) with 0
    data[~np.isfinite(data)] = 0

    # Handle empty or constant value cases
    if data.size == 0 or np.all(data == data.flat[0]):
        return np.zeros_like(data, dtype=np.float32)

    # Simple min-max normalization to reasonable elevation range
    if data.max() != data.min():
        data = (data - data.min()) * (10.0 / (data.max() - data.min()))

    return data


def extract_mesh_data(
    input_path: str, downsample_factor: int = 4, target_reduction: float = 0.9
) -> Tuple[List[List[float]], List[List[int]]]:
    """
    Extract optimized vertices and faces from GeoTIFF using robust processing.

    Args:
        input_path (str): Path to the GeoTIFF file.
        downsample_factor (int): Factor by which to downsample the raster.
        target_reduction (float): Target reduction for mesh decimation (0-1).

    Returns:
        Tuple[List[List[float]], List[List[int]]]: Vertices and faces for the mesh.
    """
    try:
        # Basic path validation
        file_path = Path(input_path)
        if not file_path.exists():
            print(f"File not found: {input_path}")
            return [], []
        if not file_path.is_file():
            print(f"Not a file: {input_path}")
            return [], []
        # Check file extension
        if file_path.suffix.lower() not in [".tif", ".tiff"]:
            print(f"Invalid file type: {input_path}")
            return [], []
        with rasterio.open(str(file_path)) as src:
            # Calculate new dimensions
            height = int(src.height // downsample_factor)
            width = int(src.width // downsample_factor)
            # Read downsampled data
            elevation_data = src.read(1, out_shape=(height, width), resampling=Resampling.average)
            # Preprocess elevation data
            elevation_data = preprocess_elevation_data(elevation_data)
            # Get transformation
            transform = src.transform * src.transform.scale((src.width / width), (src.height / height))
            # Create coordinate grid
            x = np.linspace(transform[2], transform[2] + transform[0] * width, width)
            y = np.linspace(transform[5], transform[5] + transform[4] * height, height)
            x, y = np.meshgrid(x, y)
        # Create initial mesh
        grid = pv.StructuredGrid(x, y, elevation_data)
        # Convert to triangulated mesh and optimize
        mesh = grid.extract_surface().triangulate()
        # Fast decimation using PyVista
        mesh = mesh.decimate(target_reduction)
        # Extract vertices and faces
        vertices = mesh.points.tolist()
        faces = mesh.faces.reshape(-1, 4)[:, 1:].tolist()  # Remove first index
        return vertices, faces
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        return [], []


def create_combined_terrain_ifc(
    vertices: List[List[float]], faces: List[List[int]], input_data: RequestParams
) -> bytes | None:
    """
    Fast conversion of combined terrain data to IFC with optimization.

    Args:
        vertices (List[List[float]]): List of mesh vertices.
        faces (List[List[int]]): List of mesh faces.
        input_data (RequestParams): Model and project parameters.

    Returns:
        Optional[bytes]: IFC file contents as bytes if successful, None if failed.
    """
    if not vertices or not faces:
        print("No valid terrain data to convert.")
        return None
    # Create IFC model builder
    builder = IfcModelBuilder()
    project_name, site_name, building_name = extract_project_info(input_data.containers)
    builder.build_project(project_name=project_name, site_name=site_name, building_name="DGM")
    model = builder.get_model()
    # Create contexts
    model3d = context.add_context(model, context_type="Model")
    body = context.add_context(
        model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
    )
    # Create terrain element
    element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name="DGM")
    spatial.assign_container(model, relating_structure=builder.site, products=[element])
    # Add property set for DGM
    pset_ifc = pset.add_pset(model, product=element, name="Pset_DGM")
    pset.edit_pset(
        model,
        pset=pset_ifc,
        properties={
            "_ArtDGM": "TIN",
            "_Herkunft": "SDP",
            "FaceCount": len(faces),
        },
    )
    # Add general object information
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
    representation = geometry.add_mesh_representation(
        model, context=body, vertices=[vertices], faces=[faces], edges=[[]]
    )
    geometry.assign_representation(model, product=element, representation=representation)
    ifc_snippets.assign_color_to_element(model, representation, "102, 204, 0", 0.0)
    # Extract base point from terrain
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
        output_file = PathConfig.OUTPUT / "output_dgm.ifc"
        file_path = IfcFileCreator.save_ifc_file(model, str(output_file))
        return file_path
    else:
        print("No models were processed; no IFC file was saved.")
        return None


def process_terrain_folder_to_ifc(
    folder_path: Path,
    tif_files: List[str],
    downsample_factor: int = 4,
    target_reduction: float = 0.9,
    input_data: RequestParams = None,
) -> bytes | None:
    """
    Process all GeoTIFF files in a folder and create a single combined IFC file.

    Args:
        folder_path (Path): Path to the folder containing GeoTIFF files.
        tif_files (List[str]): List of GeoTIFF filenames.
        downsample_factor (int): Downsampling factor for raster data.
        target_reduction (float): Target reduction for mesh decimation.
        input_data (RequestParams): Model and project parameters.

    Returns:
        Optional[bytes]: IFC file contents as bytes if successful, None if failed.
    """
    combined_vertices: List[List[float]] = []
    combined_faces: List[List[int]] = []
    for file in tif_files:
        file_path = folder_path / file
        print(f"Processing {file_path}...")
        vertices, faces = extract_mesh_data(str(file_path), downsample_factor, target_reduction)
        if vertices and faces:
            # Offset faces by the current number of vertices
            face_offset = len(combined_vertices)
            offset_faces = [[idx + face_offset for idx in face] for face in faces]
            combined_vertices.extend(vertices)
            combined_faces.extend(offset_faces)
    if not combined_vertices or not combined_faces:
        print("No valid terrain data found in folder.")
        return None
    return create_combined_terrain_ifc(combined_vertices, combined_faces, input_data)
