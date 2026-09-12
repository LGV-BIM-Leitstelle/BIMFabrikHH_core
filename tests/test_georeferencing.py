from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Import the functions to test
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.georeferencing.extract_elevation import (
    invalid_z,
    sample_elevations_for_points,
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


class TestSampleElevationsForPoints:
    def test_empty_points_returns_empty(self) -> None:
        out = sample_elevations_for_points(np.empty((0, 2)), ["a.tif"])
        assert out.shape == (0,)

    def test_first_valid_tile_wins(self, monkeypatch: pytest.MonkeyPatch) -> None:
        class _Src:
            def __init__(self, z: float) -> None:
                self.bounds = MagicMock(left=0, right=10, bottom=0, top=10)
                self.nodata = None
                self._z = z

            def sample(self, coords):
                return [[self._z] for _ in coords]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        files = iter([_Src(12.5), _Src(99.0)])

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
        class _Src:
            bounds = MagicMock(left=0, right=1, bottom=0, top=1)
            nodata = None

            def sample(self, coords):
                return [[5.0] for _ in coords]

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        monkeypatch.setattr(
            "BIMFabrikHH_core.core.georeferencing.extract_elevation.open_geotiff",
            lambda _path: _Src(),
        )
        points = np.array([[100.0, 200.0]])
        out = sample_elevations_for_points(points, ["a.tif"], default_elevation=-1.0)
        assert out.tolist() == [-1.0]


class TestInvalidZ:
    def test_zero_fill_nodata_and_gdal_sentinel_are_invalid(self) -> None:
        zs = np.array([5.0, 0.0, -3.4e38, np.nan, 1.2])
        mask = invalid_z(zs, nodata=-3.4e38)
        assert mask.tolist() == [False, True, True, True, False]
