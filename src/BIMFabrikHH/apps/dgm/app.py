from typing import Tuple, List

import numpy as np
import pyvista as pv
import rasterio
from ifcopenshell.api import run
from rasterio.enums import Resampling

from ...core.ifc_modelbuilder import IfcModelBuilder
from ...core.ifc_snippets import IfcSnippets
from ...core.ifc_utils import IfcFileCreator

ifc_snippets = IfcSnippets()


def preprocess_elevation_data(elevation_data: np.ndarray) -> np.ndarray:
    """
    Ultra-fast preprocessing of elevation data with minimal operations.

    Args:
        elevation_data: Raw elevation data from rasterio

    Returns:
        Processed elevation data ready for mesh generation
    """
    # Convert to float32 for memory efficiency
    data = elevation_data.astype(np.float32)

    # Quick fix for invalid values
    data[~np.isfinite(data)] = 0

    # Handle empty or constant value cases
    if data.size == 0 or np.all(data == data.flat[0]):
        return np.zeros_like(data, dtype=np.float32)

    # Simple min-max normalization to reasonable elevation range
    if data.max() != data.min():
        data = (data - data.min()) * (10.0 / (data.max() - data.min()))

    return data


def extract_mesh_data(
    input_path: str,
    downsample_factor: int = 4,
    target_reduction: float = 0.9,
) -> Tuple[List[List[float]], List[List[int]]]:
    """
    Extract optimized vertices and faces from GeoTIFF using robust processing.
    """
    try:
        with rasterio.open(input_path) as src:
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


# Rest of the code remains the same as in the previous version
def create_combined_terrain_ifc(
    vertices: List[List[float]],
    faces: List[List[int]],
    project_name: str = "Terrain Project",
    site_name: str = "Site",
) -> None:
    """
    Fast conversion of combined terrain data to IFC with optimization.
    """
    # Skip if no vertices
    if not vertices or not faces:
        print("No valid terrain data to convert.")
        return

    # Create IFC
    builder = IfcModelBuilder()
    builder.build_project(project_info_dict={"name": project_name}, site_name=site_name)
    model = builder.get_model()

    # Create contexts
    model3d = run("context.add_context", model, context_type="Model")
    body = run(
        "context.add_context",
        model,
        context_type="Model",
        context_identifier="Body",
        target_view="MODEL_VIEW",
        parent=model3d,
    )

    # Create terrain element
    element = run(
        "root.create_entity",
        model,
        ifc_class="IfcSite",
        name="Terrain",
    )

    # Add property set
    pset = run("pset.add_pset", model, product=element, name="Pset_TerrainInformation")
    run(
        "pset.edit_pset",
        model,
        pset=pset,
        properties={
            "TerrainType": "DigitalElevationModel",
            "FaceCount": len(faces),
        },
    )

    # Create and assign geometry
    representation = run(
        "geometry.add_mesh_representation",
        model,
        context=body,
        vertices=[vertices],
        faces=[faces],
        edges=[[]],
    )

    run(
        "geometry.assign_representation",
        model,
        product=element,
        representation=representation,
    )

    ifc_snippets.assign_color_to_element(model, representation, "102, 204, 0", 0.0)

    # model.write(output_path)

    if model:
        IfcFileCreator.save_ifc_file(model, "DGM_Test.ifc")
        print("*" * 200)
        print("Ifc file saved")
        print("*" * 200)

        ifc_bytes = IfcFileCreator.save_ifc_in_memory(model)
        return ifc_bytes

    else:
        print("No models were processed; no IFC file was saved.")


def process_folder_to_ifc(
    folder_path,
    tif_files,
    # output_path: str,
    downsample_factor: int = 4,
    target_reduction: float = 0.9,
) -> None:
    """
    Process all GeoTIFF files in a folder and create a single combined IFC file.
    """
    # List all GeoTIFF files
    # tif_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.endswith(".tif")]
    # print(f"Found {len(tif_files)} GeoTIFF files in the folder.")

    combined_vertices = []
    combined_faces = []

    # Loop through files and process each
    for file in tif_files:
        file_path = folder_path / file

        print(f"Processing {file_path}...")
        vertices, faces = extract_mesh_data(file_path, downsample_factor, target_reduction)

        # Only add if valid data
        if vertices and faces:
            # Adjust face indices for combined mesh
            face_offset = len(combined_vertices)
            combined_faces.extend([[v + face_offset for v in face] for face in faces])
            combined_vertices.extend(vertices)

    print(f"Combined mesh: {len(combined_faces)} faces from {len(tif_files)} files")

    # Create and write IFC
    ifc_bytes = create_combined_terrain_ifc(vertices=combined_vertices, faces=combined_faces)

    return ifc_bytes
