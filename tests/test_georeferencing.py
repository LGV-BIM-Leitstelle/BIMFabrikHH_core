from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Import the functions to test
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from affine import Affine
from rasterio.io import MemoryFile

from BIMFabrikHH_core.core.georeferencing.extract_elevation import (
    invalid_z,
    sample_elevations_for_points,
    sample_elevations_from_raster,
)


class TestCrsTransform:
    """Test cases for CRS transformation functions."""

    @patch("BIMFabrikHH_core.core.georeferencing.crs_transform.Transformer")
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

    @patch("BIMFabrikHH_core.core.georeferencing.crs_transform.Transformer")
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

    @patch("BIMFabrikHH_core.core.georeferencing.crs_transform.Transformer")
    def test_bbox_wgs84_to_epsg25832_transformation_error(self, mock_transformer):
        """Test bbox transformation with transformation error."""
        # Mock the transformer to raise an error
        mock_transformer_instance = MagicMock()
        mock_transformer.from_crs.return_value = mock_transformer_instance
        mock_transformer_instance.transform.side_effect = Exception("Transformation failed")

        bbox = (8.5, 53.5, 9.0, 54.0)

        with pytest.raises(Exception):
            bbox_wgs84_to_epsg25832(bbox)


def _memory_raster(z: np.ndarray | float, *, size: int):
    """Open a ``size`` x ``size`` m GeoTIFF in memory with origin (0, 0) and 1 m pixels."""
    grid = np.broadcast_to(np.asarray(z, dtype="float32"), (size, size))
    memfile = MemoryFile()
    with memfile.open(
        driver="GTiff",
        width=size,
        height=size,
        count=1,
        dtype="float32",
        crs="EPSG:25832",
        transform=Affine(1.0, 0.0, 0.0, 0.0, -1.0, float(size)),
    ) as dst:
        dst.write(grid, 1)
    src = memfile.open()
    src.memfile = memfile
    return src


class TestSampleElevationsFromRaster:
    def test_nearest_pixel_outside_and_fill_values(self) -> None:
        grid = np.array([[1.0, 2.0, 3.0], [4.0, 0.0, 6.0], [7.0, 8.0, 9.0]])
        with _memory_raster(grid, size=3) as src:
            x = np.array([0.5, 2.9, 1.5, 3.5, -0.1, 0.0])
            y = np.array([2.5, 0.1, 1.5, 1.0, 1.0, 0.0])
            out = sample_elevations_from_raster(src, x, y)
        assert out[:2].tolist() == [1.0, 9.0]
        assert np.isnan(out[2]), "0.0 DGM fill is missing"
        assert np.isnan(out[3]) and np.isnan(out[4]), "outside the raster is missing"
        assert np.isnan(out[5]), "the bottom edge lies below the last pixel row"

    def test_empty_input(self) -> None:
        with _memory_raster(1.0, size=2) as src:
            assert sample_elevations_from_raster(src, np.array([]), np.array([])).shape == (0,)


class TestSampleElevationsForPoints:
    def test_empty_points_returns_empty(self) -> None:
        out = sample_elevations_for_points(np.empty((0, 2)), ["a.tif"])
        assert out.shape == (0,)

    def test_first_valid_tile_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        files = iter([_memory_raster(12.5, size=10), _memory_raster(99.0, size=10)])

        def _open(_path):
            return next(files)

        monkeypatch.setattr(
            "BIMFabrikHH_core.core.georeferencing.extract_elevation.open_geotiff",
            _open,
        )
        points = np.array([[1.0, 2.0], [3.0, 4.0]])
        out = sample_elevations_for_points(points, ["a.tif", "b.tif"])
        assert out.tolist() == [12.5, 12.5]

    def test_uncovered_points_use_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "BIMFabrikHH_core.core.georeferencing.extract_elevation.open_geotiff",
            lambda _path: _memory_raster(5.0, size=1),
        )
        points = np.array([[100.0, 200.0]])
        out = sample_elevations_for_points(points, ["a.tif"], default_elevation=-1.0)
        assert out.tolist() == [-1.0]


class TestInvalidZ:
    def test_zero_fill_nodata_and_gdal_sentinel_are_invalid(self) -> None:
        zs = np.array([5.0, 0.0, -3.4e38, np.nan, 1.2])
        mask = invalid_z(zs, nodata=-3.4e38)
        assert mask.tolist() == [False, True, True, True, False]
