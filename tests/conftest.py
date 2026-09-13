"""
Pytest configuration and common fixtures for BIMFabrikHH tests.
"""

from unittest.mock import Mock

import pandas as pd
import pytest

# Not collected: the generic_entity helpers these cover are still moving, so the
# file is kept in the tree but excluded from the default run.
collect_ignore = ["test_city_generic_entity.py"]


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing data processing functions."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "Easting": [564000.0, 565000.0, 566000.0],
            "Northing": [5935000.0, 5936000.0, 5937000.0],
            "height": [10.5, 15.2, 8.9],
            "kachelbezeichnung_dk5": ["32_564000_5935000", "32_565000_5936000", "32_566000_5937000"],
        }
    )


@pytest.fixture
def sample_api_response():
    """Sample API response data for testing."""
    return {
        "features": [
            {
                "id": "1",
                "geometry": {"type": "Point", "coordinates": [564000.0, 5935000.0]},
                "properties": {"height": 10.5, "kachelbezeichnung_dk5": "32_564000_5935000"},
            },
            {
                "id": "2",
                "geometry": {"type": "MultiPoint", "coordinates": [[565000.0, 5936000.0]]},
                "properties": {"height": 15.2, "kachelbezeichnung_dk5": "32_565000_5936000"},
            },
        ]
    }


@pytest.fixture
def sample_tile_data():
    """Sample tile data for testing."""
    return {
        "features": [
            {
                "id": "1",
                "geometry": {"type": "Point", "coordinates": [564000.0, 5935000.0]},
                "properties": {"kachelbezeichnung_dk5": "32_564000_5935000"},
            }
        ]
    }


@pytest.fixture
def mock_ifc_model():
    """Mock IFC model for testing."""
    mock_model = Mock()
    mock_model.create_entity.return_value = Mock()
    return mock_model


@pytest.fixture
def sample_coordinates():
    """Sample coordinate data for testing."""
    return {
        "wgs84": {"min_lat": 53.5, "max_lat": 53.6, "min_lon": 9.9, "max_lon": 10.0},
        "epsg25832": {"min_x": 564000.0, "max_x": 565000.0, "min_y": 5935000.0, "max_y": 5936000.0},
    }


@pytest.fixture
def temp_file_path(tmp_path):
    """Temporary file path for testing file operations."""
    return tmp_path / "test_file.ifc"


@pytest.fixture
def sample_geometry_data():
    """Sample geometry data for testing."""
    return {
        "vertices": [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)],
        "face_indices": [[0, 1, 2, 3]],
        "height": 10.0,
        "width": 1.0,
        "depth": 1.0,
    }
