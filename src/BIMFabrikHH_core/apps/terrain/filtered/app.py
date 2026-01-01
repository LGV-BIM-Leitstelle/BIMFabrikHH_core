from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple, Union

import ifcopenshell.util.shape_builder
import numpy as np
import rasterio
from ifcopenshell.api import context, geometry, pset, root, spatial
from rasterio.io import MemoryFile
from scipy.spatial import Delaunay

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

logger = get_level_logger("terrain_filtered_app")


def _is_url(path: Union[str, Path]) -> bool:
    """Check if a path is a URL."""
    path_str = str(path)
    return path_str.startswith(("http://", "https://"))


def _download_to_memory(url: str, timeout: int = 120) -> Optional[BytesIO]:
    """Download a file from URL into memory."""
    import requests

    try:
        logger.info(f"Downloading from: {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        buffer = BytesIO(response.content)
        logger.info(f"Downloaded {len(response.content) / 1024 / 1024:.2f} MB to memory")
        return buffer
    except Exception as e:
        logger.error(f"Failed to download: {e}")
        return None


ifc_snippets = IfcSnippets()


class TerrainModularApp:
    """Modular terrain application for processing GeoTIFF files and creating IFC models."""

    def __init__(self, tif_files: List[str]):
        """Initialize the terrain app with a list of GeoTIFF files.

        Args:
            tif_files: List of paths to GeoTIFF files
        """
        self.tif_files = tif_files
        self.raw_terrain_data = []
        self.processed_terrain_data = None

    def get_data_in_bbox(self, bbox) -> List:
        """Get terrain data within the specified bounding box.

        Args:
            bbox: BoundingBoxParams object defining the area of interest

        Returns:
            List of terrain data (placeholder for now)
        """
        # For now, just return the tif files as "raw terrain"
        # In a real implementation, this would filter the data by bbox
        self.raw_terrain_data = self.tif_files
        return self.raw_terrain_data

    def process_data(self, raw_terrain: List) -> dict:
        """Process the raw terrain data.

        Args:
            raw_terrain: Raw terrain data from get_data_in_bbox

        Returns:
            Processed terrain data dictionary
        """
        # For now, just return a placeholder
        self.processed_terrain_data = {"processed": True, "files": raw_terrain}
        return self.processed_terrain_data

    def create_ifc(self, processed_terrain: dict, request_params: RequestParams) -> Path:
        """Create IFC model from processed terrain data.

        Args:
            processed_terrain: Processed terrain data from process_data
            request_params: Request parameters containing project info

        Returns:
            Path to the created IFC file
        """
        # Use the existing process_terrain_folder_to_ifc function
        # Convert tif_files to Path objects
        folder_path = Path(self.tif_files[0]).parent if self.tif_files else Path(".")
        tif_filenames = [Path(f).name for f in self.tif_files]

        # Call the existing function
        result = process_terrain_folder_to_ifc(
            folder_path=folder_path,
            tif_files=tif_filenames,
            min_points=1000,
            importance_threshold=0.1,
            input_data=request_params,
            move_to_origin=False,
        )

        if result:
            return result
        else:
            raise RuntimeError("Failed to create IFC model")


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
    x_grid, y_grid = np.meshgrid(x, y)

    # Select points where importance > threshold
    mask = importance > importance_threshold

    # Ensure minimum number of points
    if np.sum(mask) < min_points:
        # Take top min_points by importance
        flat_importance = importance.flatten()
        threshold = np.sort(flat_importance)[-min_points]
        mask = importance > threshold

    # Extract coordinates and elevations
    x_coords = x_grid[mask]
    y_coords = y_grid[mask]
    z_values = elevation_data[mask]

    return x_coords, y_coords, z_values


def create_boundary_points(
    bbox: Tuple[float, float, float, float], spacing: float = 5.0
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Create boundary point coordinates along all 4 edges of the bounding box.

    Args:
        bbox: Bounding box as (min_x, min_y, max_x, max_y)
        spacing: Distance between boundary points in meters

    Returns:
        Tuple of (boundary_x, boundary_y) coordinate arrays
    """
    min_x, min_y, max_x, max_y = bbox

    # Calculate number of points per edge based on spacing
    width = max_x - min_x
    height = max_y - min_y
    n_points_x = max(2, int(width / spacing) + 1)
    n_points_y = max(2, int(height / spacing) + 1)

    boundary_x = []
    boundary_y = []

    # Bottom edge (y = min_y)
    for x in np.linspace(min_x, max_x, n_points_x):
        boundary_x.append(x)
        boundary_y.append(min_y)

    # Top edge (y = max_y)
    for x in np.linspace(min_x, max_x, n_points_x):
        boundary_x.append(x)
        boundary_y.append(max_y)

    # Left edge (x = min_x), excluding corners
    for y in np.linspace(min_y, max_y, n_points_y)[1:-1]:
        boundary_x.append(min_x)
        boundary_y.append(y)

    # Right edge (x = max_x), excluding corners
    for y in np.linspace(min_y, max_y, n_points_y)[1:-1]:
        boundary_x.append(max_x)
        boundary_y.append(y)

    return np.array(boundary_x), np.array(boundary_y)


def sample_elevations_from_raster(src, x_coords: np.ndarray, y_coords: np.ndarray) -> np.ndarray:
    """
    Sample elevation values directly from a rasterio dataset.

    Args:
        src: Open rasterio dataset
        x_coords: Array of x coordinates (UTM)
        y_coords: Array of y coordinates (UTM)

    Returns:
        Array of elevation values (NaN for points outside raster)
    """
    # Create coordinate pairs for sampling
    coords = list(zip(x_coords, y_coords))

    # Sample from raster - returns generator of arrays
    samples = list(src.sample(coords))

    # Extract first band value from each sample
    elevations = np.array([s[0] if len(s) > 0 else np.nan for s in samples])

    return elevations


def filter_and_add_boundary(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    z_values: np.ndarray,
    boundary_x: np.ndarray,
    boundary_y: np.ndarray,
    boundary_z: np.ndarray,
    bbox: Tuple[float, float, float, float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Filter interior points to bbox and combine with boundary points.

    Args:
        x_coords, y_coords, z_values: Interior terrain points
        boundary_x, boundary_y, boundary_z: Boundary points with elevations
        bbox: Bounding box as (min_x, min_y, max_x, max_y)

    Returns:
        Combined (x, y, z) arrays
    """
    min_x, min_y, max_x, max_y = bbox

    # Filter interior points to bbox
    inside_mask = (x_coords >= min_x) & (x_coords <= max_x) & (y_coords >= min_y) & (y_coords <= max_y)
    x_coords = x_coords[inside_mask]
    y_coords = y_coords[inside_mask]
    z_values = z_values[inside_mask]

    # Remove boundary points with invalid elevations (NaN)
    valid_boundary = ~np.isnan(boundary_z)
    boundary_x = boundary_x[valid_boundary]
    boundary_y = boundary_y[valid_boundary]
    boundary_z = boundary_z[valid_boundary]

    # Combine
    combined_x = np.concatenate([x_coords, boundary_x])
    combined_y = np.concatenate([y_coords, boundary_y])
    combined_z = np.concatenate([z_values, boundary_z])

    logger.info(f"Added {len(boundary_x)} boundary points (from GeoTIFF), {len(x_coords)} interior points")

    return combined_x, combined_y, combined_z


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
        logger.error("Not enough points for triangulation (minimum 3 required)")
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
        logger.error(f"Error during mesh generation: {e}")
        return [], []


def extract_optimized_mesh_data(
    input_path: Path,
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    input_data: Optional[RequestParams] = None,
) -> Tuple[List[List[float]], List[List[int]]]:
    """
    Extract optimized mesh data from GeoTIFF using adaptive sampling.

    Args:
        input_path: Path to the GeoTIFF file
        min_points: Minimum number of points to keep
        importance_threshold: Threshold for point importance (0-1)
        input_data: Request parameters containing project info

    Returns:
        Tuple of (vertices, faces) for the optimized mesh
    """
    try:
        # Basic path validation
        file_path = Path(input_path)
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"Invalid file path: {input_path}")
            return [], []

        # Check file extension
        if file_path.suffix.lower() not in [".tif", ".tiff"]:
            logger.error(f"Invalid file type: {input_path}")
            return [], []

        with rasterio.open(str(file_path)) as src:
            # Read elevation data
            elevation_data = src.read(1)

            if elevation_data.size == 0:
                logger.error(f"Empty elevation data in file: {input_path}")
                return [], []

            # Get the transform for coordinate conversion
            transform = src.transform

            # Perform adaptive sampling
            x_coords, y_coords, z_values = adaptive_sampling(
                elevation_data, transform, min_points=min_points, importance_threshold=importance_threshold
            )

            # --- BBOX FILTER ---
            if input_data is not None and hasattr(input_data, "bbox"):
                bbox_wgs84 = (
                    input_data.bbox.min_x,
                    input_data.bbox.min_y,
                    input_data.bbox.max_x,
                    input_data.bbox.max_y,
                )
                bbox = bbox_wgs84_to_epsg25832(bbox_wgs84)
                buffer = 50  # meters
                expanded_bbox = (bbox[0] - buffer, bbox[1] - buffer, bbox[2] + buffer, bbox[3] + buffer)
                logger.info(f"Expanded BBox (UTM): {expanded_bbox}")
                logger.info(f"Raster bounds: {src.bounds}")
                # Filter points inside expanded bbox
                inside = (
                    (x_coords >= expanded_bbox[0])
                    & (x_coords <= expanded_bbox[2])
                    & (y_coords >= expanded_bbox[1])
                    & (y_coords <= expanded_bbox[3])
                )
                x_coords = x_coords[inside]
                y_coords = y_coords[inside]
                z_values = z_values[inside]

            if len(x_coords) < 3:
                logger.error(f"Not enough valid points found in file: {input_path}")
                return [], []

            logger.info(f"Processing {len(x_coords)} points from {input_path}")

            # Generate optimized mesh
            vertices, faces = generate_optimized_mesh(x_coords, y_coords, z_values)

            if vertices and faces:
                logger.info(f"Generated mesh with {len(vertices)} vertices and {len(faces)} faces")

            return vertices, faces

    except Exception as e:
        logger.error(f"Error processing {input_path}: {e}")
        return [], []


def create_terrain_ifc(
    vertices: List[List[float]],
    faces: List[List[int]],
    input_data: RequestParams,
    nullpunkt_x: float = 0,
    nullpunkt_y: float = 0,
    output_path: Optional[Path] = None,
) -> Optional[bytes]:
    """
    Convert terrain mesh data to IFC format.

    Args:
        vertices: List of [x,y,z] coordinates
        faces: List of triangle indices
        input_data: Request parameters containing project info
        nullpunkt_x: X coordinate of the nullpunkt
        nullpunkt_y: Y coordinate of the nullpunkt
        output_path: Optional full path where to save the IFC file.
            If provided, saves to that path and returns bytes.
            If None, saves to default location and returns bytes.

    Returns:
        IFC file contents as bytes, or None if conversion fails
    """
    if not vertices or not faces:
        logger.warning("No valid terrain data to convert.")
        return None

    try:
        logger.info(f"\nCreating IFC model with {len(vertices)} vertices and {len(faces)} faces...")

        # Create IFC
        builder = IfcModelBuilder()
        project_name, site_name, building_name = extract_project_info(input_data.containers)

        builder.build_project(
            project_name=project_name,
            coordinate_system=CoordinateSystemTemplates.epsg_25832(),
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name=site_name,
            building_name="DGM",
        )
        model = builder.model

        if not model:
            logger.error("Failed to create IFC model")
            return None

        # Create contexts
        logger.info("Creating IFC contexts...")
        model3d = context.add_context(model, context_type="Model")
        body = context.add_context(
            model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
        )

        # Create terrain element
        logger.info("Creating terrain element...")
        element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name="DGM")
        if not element:
            logger.error("Failed to create terrain element")
            return None

        spatial.assign_container(model, relating_structure=builder.site, products=[element])

        # Add property sets
        logger.info("Adding property sets...")
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
        logger.info("Creating mesh representation...")
        representation = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices], faces=[faces], edges=[[]]
        )

        if not representation:
            logger.error("Failed to create mesh representation")
            return None

        logger.info("Assigning representation to element...")
        geometry.assign_representation(model, product=element, representation=representation)
        ifc_snippets.assign_color_to_element(model, representation, "102, 204, 0", 0.0)

        # Create shape builder after model is built
        shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

        # Use provided nullpunkt_x, nullpunkt_y for base point
        pset_groups = extract_psets_basepoint(input_data.containers)
        # Create basepoint using old approach
        basepoint_data = {"position": (nullpunkt_x, nullpunkt_y, 0), "size": 5.0, "psets": pset_groups}
        # Create basepoint manually without using BIMFactoryElement
        from BIMFabrikHH_core.core.geometry.advanced_objects import create_basepoint_quad

        basepoint_quad = create_basepoint_quad(size=5.0, psets=pset_groups)
        basepoint_entity = basepoint_quad.build(model)

        # Position the basepoint
        import numpy as np

        matrix = np.eye(4)
        matrix[0, 3] = nullpunkt_x  # X position
        matrix[1, 3] = nullpunkt_y  # Y position
        matrix[2, 3] = 0  # Z position
        geometry.edit_object_placement(model, matrix=matrix, product=basepoint_entity)

        # Assign to site
        if builder.site:
            spatial.assign_container(model, relating_structure=builder.site, products=[basepoint_entity])
        else:
            # Create a storey as fallback
            storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
            spatial.assign_container(model, relating_structure=storey, products=[basepoint_entity])

        if model:
            logger.info("Saving IFC model...")
            file_path = builder.save_ifc_to_output("output_dgm_optimized.ifc", output_path=output_path)

            if file_path is None:
                logger.error("Failed to save IFC file")
                return None

            # Read the saved file and return as bytes
            with open(file_path, "rb") as f:
                return f.read()
        else:
            logger.error("Failed to create IFC model")
            return None

    except Exception as e:
        logger.error(f"Error creating IFC model: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def extract_combined_points(
    folder_path: Path,
    tif_files: List[str],
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    input_data: Optional[RequestParams] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract and combine points from all GeoTIFF files, including boundary points sampled directly from GeoTIFF.

    Args:
        folder_path: Path to folder containing GeoTIFF files
        tif_files: List of GeoTIFF filenames to process
        min_points: Minimum number of points to keep per file
        importance_threshold: Threshold for point importance (0-1)
        input_data: Request parameters containing project info

    Returns:
        Tuple of (x_coords, y_coords, z_values) arrays containing all points including boundary
    """
    all_x_coords = []
    all_y_coords = []
    all_z_values = []

    # Get bounding box in UTM coordinates
    bbox = None
    boundary_x = None
    boundary_y = None
    boundary_z = None

    if input_data is not None and hasattr(input_data, "bbox"):
        bbox_wgs84 = (
            input_data.bbox.min_x,
            input_data.bbox.min_y,
            input_data.bbox.max_x,
            input_data.bbox.max_y,
        )
        bbox = bbox_wgs84_to_epsg25832(bbox_wgs84)
        buffer_size = 100  # meters for data collection
        expanded_bbox = (bbox[0] - buffer_size, bbox[1] - buffer_size, bbox[2] + buffer_size, bbox[3] + buffer_size)
        logger.info(f"Expanded BBox (UTM): {expanded_bbox}")

        # Create boundary points coordinates (will sample elevations from GeoTIFF)
        boundary_x, boundary_y = create_boundary_points(bbox, spacing=5.0)
        boundary_z = np.full(len(boundary_x), np.nan)  # Will be filled from GeoTIFF

    # Check if folder_path is a URL
    is_url_path = _is_url(folder_path)

    # Process each file
    for file in tif_files:
        if is_url_path:
            file_path = f"{folder_path}/{file}"
        else:
            file_path = folder_path / file
        logger.info(f"Processing {file_path}...")

        try:
            # Handle URL vs local file
            if is_url_path:
                mem_buffer = _download_to_memory(str(file_path))
                if mem_buffer is None:
                    logger.warning(f"Failed to download: {file_path}")
                    continue
                context_manager = MemoryFile(mem_buffer)
            else:
                context_manager = rasterio.open(str(file_path))

            with context_manager as memfile_or_src:
                # For MemoryFile, we need to open it; for rasterio.open it's already open
                if is_url_path:
                    src = memfile_or_src.open()
                else:
                    src = memfile_or_src

                try:
                    # Read elevation data
                    elevation_data = src.read(1)
                    if elevation_data.size == 0:
                        logger.warning(f"Empty elevation data in file: {file_path}")
                        continue

                    # Get the transform for coordinate conversion
                    transform = src.transform
                    logger.info(f"Raster bounds: {src.bounds}")

                    # Perform adaptive sampling for interior points
                    x_coords, y_coords, z_values = adaptive_sampling(
                        elevation_data, transform, min_points=min_points, importance_threshold=importance_threshold
                    )

                    # Filter points inside expanded bbox if provided
                    if bbox is not None:
                        inside = (
                            (x_coords >= expanded_bbox[0])
                            & (x_coords <= expanded_bbox[2])
                            & (y_coords >= expanded_bbox[1])
                            & (y_coords <= expanded_bbox[3])
                        )
                        x_coords = x_coords[inside]
                        y_coords = y_coords[inside]
                        z_values = z_values[inside]

                    if len(x_coords) > 0:
                        all_x_coords.append(x_coords)
                        all_y_coords.append(y_coords)
                        all_z_values.append(z_values)
                        logger.info(f"Added {len(x_coords)} points from {file_path}")

                    # Sample boundary point elevations from this GeoTIFF (if they fall within it)
                    if boundary_x is not None and len(boundary_x) > 0:
                        bounds = src.bounds
                        # Find boundary points that fall within this raster
                        in_raster = (
                            (boundary_x >= bounds.left)
                            & (boundary_x <= bounds.right)
                            & (boundary_y >= bounds.bottom)
                            & (boundary_y <= bounds.top)
                        )
                        if np.any(in_raster):
                            # Sample elevations for these points
                            sampled_z = sample_elevations_from_raster(src, boundary_x[in_raster], boundary_y[in_raster])
                            # Update boundary_z where we got valid values
                            boundary_z[in_raster] = np.where(
                                np.isnan(boundary_z[in_raster]), sampled_z, boundary_z[in_raster]
                            )
                            logger.info(f"Sampled {np.sum(in_raster)} boundary elevations from GeoTIFF")

                finally:
                    if is_url_path:
                        src.close()

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            continue

    # Combine all interior points
    if not all_x_coords:
        return np.array([]), np.array([]), np.array([])

    x_coords = np.concatenate(all_x_coords)
    y_coords = np.concatenate(all_y_coords)
    z_values = np.concatenate(all_z_values)

    logger.info(f"Combined {len(x_coords)} interior points from {len(tif_files)} files")

    # Filter and add boundary points
    if bbox is not None and boundary_x is not None:
        x_coords, y_coords, z_values = filter_and_add_boundary(
            x_coords, y_coords, z_values, boundary_x, boundary_y, boundary_z, bbox
        )

    return x_coords, y_coords, z_values


def process_terrain_folder_to_ifc(
    folder_path: Path,
    tif_files: List[str],
    min_points: int = 1000,
    importance_threshold: float = 0.1,
    input_data: Optional[RequestParams] = None,
    move_to_origin: bool = False,
    output_path: Optional[Path] = None,
) -> Optional[bytes]:
    """
    Process multiple GeoTIFF files and create a combined IFC file.

    Args:
        folder_path: Path or URL to folder containing GeoTIFF files
        tif_files: List of GeoTIFF filenames to process
        min_points: Minimum number of points to keep per file
        importance_threshold: Threshold for point importance (0-1)
        input_data: Request parameters containing project info
        move_to_origin: Whether to move the mesh to the origin
        output_path: Optional full path where to save the IFC file.
            If provided, saves to that path. If None, saves to default location.

    Returns:
        Combined IFC file contents as bytes, or None if processing fails
    """
    # Collect all points from all tiles (including boundary points sampled from GeoTIFF)
    x_coords, y_coords, z_values = extract_combined_points(
        folder_path=folder_path,
        tif_files=tif_files,
        min_points=min_points,
        importance_threshold=importance_threshold,
        input_data=input_data,
    )

    if len(x_coords) < 3:
        logger.error("Not enough valid points found in all files")
        return None

    # Generate a single optimized mesh from all points (including boundary)
    vertices, faces = generate_optimized_mesh(x_coords, y_coords, z_values)

    if not vertices or not faces:
        logger.error("Failed to generate mesh from points")
        return None

    # Round coordinates for consistency
    arr = np.array(vertices)
    arr[:, 0] = np.round(arr[:, 0], 6)  # X
    arr[:, 1] = np.round(arr[:, 1], 6)  # Y
    arr[:, 2] = np.round(arr[:, 2], 4)  # Z (height)
    vertices = arr.tolist()

    # Move to origin if requested
    bbox = None
    if input_data is not None and hasattr(input_data, "bbox"):
        bbox_wgs84 = (input_data.bbox.min_x, input_data.bbox.min_y, input_data.bbox.max_x, input_data.bbox.max_y)
        bbox = bbox_wgs84_to_epsg25832(bbox_wgs84)

    if move_to_origin and bbox is not None and vertices:
        arr = np.array(vertices)
        arr[:, 0] -= bbox[0]
        arr[:, 1] -= bbox[1]
        vertices = arr.tolist()
        nullpunkt_x, nullpunkt_y = 0, 0
    elif bbox is not None:
        nullpunkt_x, nullpunkt_y = bbox[0], bbox[1]
    else:
        nullpunkt_x, nullpunkt_y = vertices[0][0], vertices[0][1] if vertices else (0, 0)

    logger.info(f"Created mesh with {len(vertices)} vertices and {len(faces)} faces")

    return create_terrain_ifc(
        vertices=vertices,
        faces=faces,
        input_data=input_data,
        nullpunkt_x=nullpunkt_x,
        nullpunkt_y=nullpunkt_y,
        output_path=output_path,
    )
