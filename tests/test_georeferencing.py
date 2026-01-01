from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Import the functions to test
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.georeferencing.extract_elevation import (
    extract_elevation_df_from_geotiff,
    extract_elevation_point_from_geotiff,
)


class TestCrsTransform:
    """Test cases for CRS transformation functions."""

    @patch("BIMFabrikHH.core.georeferencing.crs_transform.Transformer")
    def test_bbox_wgs84_to_epsg25832_valid_input(self, mock_transformer):
        """Test bbox transformation with valid input."""
        # Mock the transformer
        mock_transformer_instance = MagicMock()
        mock_transformer.from_crs.return_value = mock_transformer_instance
        mock_transformer_instance.transform.side_effect = [
            (1000.0, 5000.0),  # First corner
            (2000.0, 6000.0),  # Second corner
        ]

        # Test input bbox (minx, miny, maxx, maxy) in WGS84
        bbox = (8.5, 53.5, 9.0, 54.0)  # Hamburg area

        result = bbox_wgs84_to_epsg25832(bbox)

        # Verify the transformer was called correctly
        mock_transformer.from_crs.assert_called_once_with("EPSG:4326", "EPSG:25832", always_xy=True)
        assert mock_transformer_instance.transform.call_count == 2

        # Verify the result
        assert isinstance(result, tuple)
        assert len(result) == 4
        assert result[0] == 1000.0  # minx
        assert result[1] == 5000.0  # miny
        assert result[2] == 2000.0  # maxx
        assert result[3] == 6000.0  # maxy

    @patch("BIMFabrikHH.core.georeferencing.crs_transform.Transformer")
    def test_bbox_wgs84_to_epsg25832_swapped_coordinates(self, mock_transformer):
        """Test bbox transformation with swapped min/max coordinates."""
        # Mock the transformer
        mock_transformer_instance = MagicMock()
        mock_transformer.from_crs.return_value = mock_transformer_instance
        mock_transformer_instance.transform.side_effect = [
            (2000.0, 6000.0),  # First corner (higher values)
            (1000.0, 5000.0),  # Second corner (lower values)
        ]

        # Test input bbox with swapped coordinates
        bbox = (9.0, 54.0, 8.5, 53.5)  # max values first

        result = bbox_wgs84_to_epsg25832(bbox)

        # Verify the result ensures min/max ordering
        assert result[0] == 1000.0  # minx
        assert result[1] == 5000.0  # miny
        assert result[2] == 2000.0  # maxx
        assert result[3] == 6000.0  # maxy

    @patch("BIMFabrikHH.core.georeferencing.crs_transform.Transformer")
    def test_bbox_wgs84_to_epsg25832_transformation_error(self, mock_transformer):
        """Test bbox transformation with transformation error."""
        # Mock the transformer to raise an error
        mock_transformer_instance = MagicMock()
        mock_transformer.from_crs.return_value = mock_transformer_instance
        mock_transformer_instance.transform.side_effect = Exception("Transformation failed")

        bbox = (8.5, 53.5, 9.0, 54.0)

        with pytest.raises(Exception):
            bbox_wgs84_to_epsg25832(bbox)


class TestExtractElevation:
    """Test cases for elevation extraction functions."""

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.sample_gen")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.rasterio")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_df_from_geotiff_valid_input(self, mock_path, mock_rasterio, mock_sample_gen):
        """Test elevation extraction from DataFrame with valid input."""
        mock_path.return_value.exists.return_value = True
        df = pd.DataFrame({"easting": [1000, 2000, 3000], "northing": [5000, 6000, 7000]})

        mock_dataset = MagicMock()
        mock_dataset.nodata = -9999
        mock_rasterio.open.return_value.__enter__.return_value = mock_dataset
        mock_sample_gen.return_value = [[100.5], [101.2], [102.0]]

        result = extract_elevation_df_from_geotiff(df, "test_dem.tif", "easting", "northing")

        assert isinstance(result, pd.DataFrame)
        assert "Elevation" in result.columns
        assert len(result) == 3
        assert result["Elevation"].tolist() == [100.5, 101.2, 102.0]

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_df_from_geotiff_file_not_found(self, mock_path):
        """Test elevation extraction with non-existent file."""
        mock_path.return_value.exists.return_value = False
        df = pd.DataFrame({"easting": [1000], "northing": [5000]})

        with pytest.raises(FileNotFoundError, match="GeoTIFF file not found: nonexistent.tif"):
            extract_elevation_df_from_geotiff(df, "nonexistent.tif", "easting", "northing")

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.rasterio")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_point_from_geotiff_single_point(self, mock_path, mock_rasterio):
        """Test elevation extraction for single point."""
        mock_path.return_value.exists.return_value = True
        mock_dataset = MagicMock()
        mock_dataset.read.return_value = np.array([[150.75]])
        mock_dataset.index.return_value = (0, 0)
        mock_dataset.height = 1
        mock_dataset.width = 1
        mock_dataset.nodata = -9999
        mock_rasterio.open.return_value.__enter__.return_value = mock_dataset

        result = extract_elevation_point_from_geotiff(1500, 5500, "test_dem.tif")

        assert isinstance(result, float)
        assert result == 150.75

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.rasterio")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_point_from_geotiff_multiple_points(self, mock_path, mock_rasterio):
        """Test elevation extraction for multiple points."""
        mock_path.return_value.exists.return_value = True
        mock_dataset = MagicMock()
        mock_dataset.sample.return_value = [[100.0], [200.0], [300.0]]
        mock_dataset.nodata = -9999
        mock_rasterio.open.return_value.__enter__.return_value = mock_dataset

        eastings = [1000.0, 2000.0, 3000.0]
        northings = [5000.0, 6000.0, 7000.0]

        result = extract_elevation_point_from_geotiff(eastings, northings, "test_dem.tif")

        assert isinstance(result, list)
        assert result == [100.0, 200.0, 300.0]

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.rasterio")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_point_from_geotiff_out_of_bounds(self, mock_path, mock_rasterio):
        """Test elevation extraction for out-of-bounds coordinates."""
        mock_path.return_value.exists.return_value = True
        mock_dataset = MagicMock()
        mock_dataset.index.return_value = (999, 999)  # Out of bounds
        mock_dataset.height = 100
        mock_dataset.width = 100
        mock_rasterio.open.return_value.__enter__.return_value = mock_dataset

        result = extract_elevation_point_from_geotiff(999999, 999999, "test_dem.tif")

        assert result == 0.0

    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.rasterio")
    @patch("BIMFabrikHH.core.georeferencing.extract_elevation.Path")
    def test_extract_elevation_point_from_geotiff_nodata_value(self, mock_path, mock_rasterio):
        """Test elevation extraction with nodata values."""
        mock_path.return_value.exists.return_value = True
        mock_dataset = MagicMock()
        mock_dataset.read.return_value = np.array([[-9999]])  # Nodata value
        mock_dataset.index.return_value = (0, 0)
        mock_dataset.height = 1
        mock_dataset.width = 1
        mock_dataset.nodata = -9999
        mock_rasterio.open.return_value.__enter__.return_value = mock_dataset

        result = extract_elevation_point_from_geotiff(1000, 5000, "test_dem.tif")

        assert result == 0.0
