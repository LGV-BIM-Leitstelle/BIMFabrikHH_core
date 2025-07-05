from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# Import the classes to test
from BIMFabrikHH.apps.trees.basic.app import BaumModeller


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
def sample_tree_data():
    """Sample tree data for testing."""
    return {
        "features": [
            {
                "id": "tree1",
                "geometry": {"type": "Point", "coordinates": [0.5, 0.5]},
                "properties": {
                    "stammumfang_bk": "314",  # 314 cm circumference = 1m diameter
                    "baumart": "Oak",
                    "height": 15.0,
                },
            }
        ]
    }


@pytest.fixture
def sample_tree_df():
    """Sample DataFrame with tree data."""
    return pd.DataFrame(
        {
            "Easting": [0.5],
            "Northing": [0.5],
            "stammumfang_bk": ["1.0000"],  # Already converted to diameter
            "baumart": ["Oak"],
            "height": [15.0],
        }
    )


@patch("BIMFabrikHH.apps.trees.basic.app.DataProcessor")
@patch("BIMFabrikHH.apps.trees.basic.app.extract_elevation_df_from_geotiff")
@patch("BIMFabrikHH.apps.trees.basic.app.extract_project_info")
@patch("BIMFabrikHH.apps.trees.basic.app.extract_level_of_geometry")
@patch("BIMFabrikHH.apps.trees.basic.app.bbox_wgs84_to_epsg25832")
@patch("BIMFabrikHH.apps.trees.basic.app.extract_psets_basepoint")
@patch("BIMFabrikHH.apps.trees.basic.app.BasePoint")
@patch("BIMFabrikHH.apps.trees.basic.app.PathConfig")
@patch("BIMFabrikHH.apps.trees.basic.app.IfcFileCreator")
def test_baum_modeller_create_tree_model_smoke(
    mock_ifcfilecreator,
    mock_pathconfig,
    mock_basepoint,
    mock_extract_psets,
    mock_bbox,
    mock_extract_level,
    mock_extract_project,
    mock_extract_elevation,
    mock_dataprocessor,
    sample_tree_data,
    mock_model_params,
    tmp_path,
):
    """Smoke test for BaumModeller.create_tree_model."""

    # Setup mocks
    mock_extract_project.return_value = ("Project", "Site", "Building")
    mock_extract_level.return_value = "LOD1"
    mock_bbox.return_value = (0, 0, 1, 1)
    mock_extract_psets.return_value = {}

    # Mock DataFrame processing
    mock_df = pd.DataFrame({"Easting": [0.5], "Northing": [0.5], "stammumfang_bk": ["1.0000"], "baumart": ["Oak"]})
    mock_dataprocessor.raw_data_to_dataframe.return_value = mock_df

    # Mock elevation extraction (no elevation file provided)
    mock_extract_elevation.return_value = mock_df

    # Mock IFC operations
    mock_model = MagicMock()
    mock_builder = MagicMock()
    mock_builder.get_model.return_value = mock_model
    mock_builder.site = MagicMock()
    mock_builder.body = MagicMock()

    # Mock BaumManager
    mock_baum_manager = MagicMock()

    # Mock file operations
    mock_pathconfig.OUTPUT = tmp_path
    mock_ifcfilecreator.save_ifc_file.return_value = tmp_path / "output_baum.ifc"

    # Create BaumModeller instance and patch its components after creation
    modeller = BaumModeller()
    modeller.builder = mock_builder
    modeller.baum_manager = mock_baum_manager

    result = modeller.create_tree_model(sample_tree_data, mock_model_params)

    # Assert that an output file path is returned
    assert result == tmp_path / "output_baum.ifc"


@patch("BIMFabrikHH.apps.trees.basic.app.MathTool")
def test_convert_umfang_durchmesser(mock_mathtool):
    """Test the convert_umfang_durchmesser static method."""

    # Setup mock
    mock_mathtool.float_4f.return_value = "1.0000"

    # Create test DataFrame
    df = pd.DataFrame({"stammumfang_bk": ["314", "628", "157"]})  # 314cm, 628cm, 157cm circumference

    # Test the conversion
    result = BaumModeller.convert_umfang_durchmesser(df, "stammumfang_bk", mock_mathtool.float_4f)

    # Verify the conversion (circumference/π = diameter)
    # 314cm / π ≈ 100cm = 1m, 628cm / π ≈ 200cm = 2m, 157cm / π ≈ 50cm = 0.5m
    assert len(result) == 3
    mock_mathtool.float_4f.assert_called()


def test_baum_modeller_init():
    """Test BaumModeller initialization."""
    modeller = BaumModeller()
    assert modeller.baum_manager is not None
    assert modeller.builder is not None
    assert modeller.model is None


@patch("BIMFabrikHH.apps.trees.basic.app.DataProcessor")
def test_raw_data_to_tree_df(mock_dataprocessor):
    """Test raw_data_to_tree_df method."""

    # Setup mock
    mock_df = pd.DataFrame({"Easting": [0.5], "Northing": [0.5], "stammumfang_bk": ["314"]})
    mock_dataprocessor.raw_data_to_dataframe.return_value = mock_df

    # Test with data that has stammumfang_bk column
    sample_data = {"features": [{"id": "1"}]}
    result = BaumModeller.raw_data_to_tree_df(sample_data)

    # Verify DataProcessor was called
    mock_dataprocessor.raw_data_to_dataframe.assert_called_once_with(sample_data)
    assert not result.empty
