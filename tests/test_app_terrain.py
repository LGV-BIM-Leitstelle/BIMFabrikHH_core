from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Import the functions to test
from BIMFabrikHH.apps.terrain.basic.app import (
    create_combined_terrain_ifc,
    extract_mesh_data,
    preprocess_elevation_data,
    process_terrain_folder_to_ifc,
)


@pytest.fixture
def mock_model_params():
    class MockBBox:
        min_x = 0
        min_y = 0
        max_x = 1
        max_y = 1

    class MockParams:
        bbox = MockBBox()
        containers = []

    return MockParams()


@pytest.fixture
def sample_elevation_data():
    """Sample elevation data for testing."""
    return np.array([[10.0, 15.0, 20.0], [12.0, 18.0, 22.0], [8.0, 14.0, 16.0]], dtype=np.float32)


def test_preprocess_elevation_data_valid():
    """Test preprocess_elevation_data with valid data."""
    data = np.array([[10.0, 15.0], [12.0, 18.0]], dtype=np.float32)
    result = preprocess_elevation_data(data)

    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32
    assert result.shape == data.shape
    assert np.all(np.isfinite(result))


def test_preprocess_elevation_data_with_nan():
    """Test preprocess_elevation_data with NaN values."""
    data = np.array([[10.0, np.nan], [12.0, 18.0]], dtype=np.float32)
    result = preprocess_elevation_data(data)

    assert isinstance(result, np.ndarray)
    assert np.all(np.isfinite(result))  # No NaN values
    assert result[0, 1] == 0.0  # NaN should be replaced with 0


def test_preprocess_elevation_data_constant():
    """Test preprocess_elevation_data with constant values."""
    data = np.full((3, 3), 15.0, dtype=np.float32)
    result = preprocess_elevation_data(data)

    assert isinstance(result, np.ndarray)
    assert np.all(result == 0.0)  # Constant data should result in zeros


def test_preprocess_elevation_data_empty():
    """Test preprocess_elevation_data with empty array."""
    data = np.array([], dtype=np.float32)
    result = preprocess_elevation_data(data)

    assert isinstance(result, np.ndarray)
    assert result.size == 0


@patch("BIMFabrikHH.apps.terrain.basic.app.rasterio")
@patch("BIMFabrikHH.apps.terrain.basic.app.pv")
@patch("BIMFabrikHH.apps.terrain.basic.app.Path")
def test_extract_mesh_data_success(mock_path, mock_pv, mock_rasterio):
    """Test extract_mesh_data with successful processing."""

    # Mock file existence check
    mock_path_instance = MagicMock()
    mock_path_instance.exists.return_value = True
    mock_path_instance.is_file.return_value = True
    mock_path_instance.suffix = ".tif"
    mock_path.return_value = mock_path_instance

    # Mock rasterio operations
    mock_src = MagicMock()
    mock_src.height = 100
    mock_src.width = 100
    mock_src.read.return_value = np.array([[10.0, 15.0], [12.0, 18.0]])
    mock_src.transform = MagicMock()
    mock_src.transform.scale.return_value = MagicMock()

    mock_rasterio.open.return_value.__enter__.return_value = mock_src

    # Mock PyVista operations
    mock_grid = MagicMock()
    mock_mesh = MagicMock()
    mock_mesh.points = np.array([[0, 0, 10], [1, 0, 15], [0, 1, 12], [1, 1, 18]])
    mock_mesh.faces = np.array([3, 0, 1, 2, 3, 1, 3, 2])  # Triangle faces

    mock_grid.extract_surface.return_value.triangulate.return_value.decimate.return_value = mock_mesh
    mock_pv.StructuredGrid.return_value = mock_grid

    # Test with valid file path
    result_vertices, result_faces = extract_mesh_data("test.tif")

    assert isinstance(result_vertices, list)
    assert isinstance(result_faces, list)
    assert len(result_vertices) > 0
    assert len(result_faces) > 0


def test_extract_mesh_data_file_not_found():
    """Test extract_mesh_data with non-existent file."""
    result_vertices, result_faces = extract_mesh_data("nonexistent.tif")

    assert result_vertices == []
    assert result_faces == []


def test_extract_mesh_data_invalid_extension():
    """Test extract_mesh_data with invalid file extension."""
    result_vertices, result_faces = extract_mesh_data("test.txt")

    assert result_vertices == []
    assert result_faces == []


@patch("BIMFabrikHH.apps.terrain.basic.app.IfcModelBuilder")
@patch("BIMFabrikHH.apps.terrain.basic.app.extract_project_info")
@patch("BIMFabrikHH.apps.terrain.basic.app.context")
@patch("BIMFabrikHH.apps.terrain.basic.app.root")
@patch("BIMFabrikHH.apps.terrain.basic.app.spatial")
@patch("BIMFabrikHH.apps.terrain.basic.app.pset")
@patch("BIMFabrikHH.apps.terrain.basic.app.geometry")
@patch("BIMFabrikHH.apps.terrain.basic.app.ifc_snippets")
@patch("BIMFabrikHH.apps.terrain.basic.app.extract_psets_basepoint")
@patch("BIMFabrikHH.apps.terrain.basic.app.BasePoint")
@patch("BIMFabrikHH.apps.terrain.basic.app.PathConfig")
@patch("BIMFabrikHH.apps.terrain.basic.app.IfcFileCreator")
def test_create_combined_terrain_ifc_smoke(
    mock_ifcfilecreator,
    mock_pathconfig,
    mock_basepoint,
    mock_extract_psets,
    mock_ifc_snippets,
    mock_geometry,
    mock_pset,
    mock_spatial,
    mock_root,
    mock_context,
    mock_extract_project,
    mock_builder,
    mock_model_params,
    tmp_path,
):
    """Smoke test for create_combined_terrain_ifc."""

    # Setup mocks
    mock_extract_project.return_value = ("Project", "Site", "Building")
    mock_extract_psets.return_value = {}

    # Mock IFC operations
    mock_model = MagicMock()
    mock_builder.return_value.get_model.return_value = mock_model
    mock_builder.return_value.site = MagicMock()
    mock_builder.return_value.body = MagicMock()

    mock_context.add_context.return_value = MagicMock()
    mock_root.create_entity.return_value = MagicMock()
    mock_pset.add_pset.return_value = MagicMock()
    mock_geometry.add_mesh_representation.return_value = MagicMock()

    # Mock file operations
    mock_pathconfig.OUTPUT = tmp_path
    mock_ifcfilecreator.save_ifc_file.return_value = tmp_path / "output_dgm.ifc"

    # Test data
    vertices = [[0.0, 0.0, 10.0], [1.0, 0.0, 15.0], [0.0, 1.0, 12.0], [1.0, 1.0, 18.0]]
    faces = [[0, 1, 2], [1, 3, 2]]

    # Call the function
    result = create_combined_terrain_ifc(vertices, faces, mock_model_params)

    # Assert that an output file path is returned
    assert result == tmp_path / "output_dgm.ifc"


def test_create_combined_terrain_ifc_empty_data(mock_model_params):
    """Test create_combined_terrain_ifc with empty data."""
    result = create_combined_terrain_ifc([], [], mock_model_params)
    assert result is None


@patch("BIMFabrikHH.apps.terrain.basic.app.extract_mesh_data")
@patch("BIMFabrikHH.apps.terrain.basic.app.create_combined_terrain_ifc")
def test_process_terrain_folder_to_ifc_smoke(mock_create_combined, mock_extract_mesh, mock_model_params, tmp_path):
    """Smoke test for process_terrain_folder_to_ifc."""

    # Setup mocks
    mock_extract_mesh.return_value = ([[0, 0, 10], [1, 0, 15]], [[0, 1, 2]])  # vertices  # faces
    mock_create_combined.return_value = tmp_path / "output_dgm.ifc"

    # Test data
    tif_files = ["test1.tif", "test2.tif"]

    # Call the function
    result = process_terrain_folder_to_ifc(folder_path=tmp_path, tif_files=tif_files, input_data=mock_model_params)

    # Assert that extract_mesh_data was called for each file
    assert mock_extract_mesh.call_count == len(tif_files)

    # Assert that create_combined_terrain_ifc was called
    mock_create_combined.assert_called_once()

    # Assert that a result was returned
    assert result == tmp_path / "output_dgm.ifc"
