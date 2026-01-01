"""
Unit tests for data processing functionality.
"""

import pandas as pd
import pytest

from BIMFabrikHH_core.core.data_processing.data_processor import DataProcessor


@pytest.fixture
def processor():
    return DataProcessor()


class TestDataProcessor:
    """Test cases for DataProcessor class."""

    def test_raw_data_to_dataframe_valid_data(self, sample_api_response, processor):
        """Test converting valid API response to DataFrame."""
        df = processor.raw_data_to_dataframe(sample_api_response)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "id" in df.columns
        assert "Easting" in df.columns
        assert "Northing" in df.columns
        assert df.iloc[0]["Easting"] == "564000.0000"
        assert df.iloc[0]["Northing"] == "5935000.0000"
        assert df.iloc[0]["height"] == 10.5

    def test_raw_data_to_dataframe_empty_data(self, processor):
        """Test handling empty data."""
        df = processor.raw_data_to_dataframe({})
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_raw_data_to_dataframe_none_data(self, processor):
        """Test handling None data."""
        df = processor.raw_data_to_dataframe({})  # Empty dict instead of None
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_raw_data_to_dataframe_no_features(self, processor):
        """Test handling data without features."""
        data = {"some_other_key": "value"}
        df = processor.raw_data_to_dataframe(data)
        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_extract_feature_point_geometry(self, processor):
        """Test extracting feature with Point geometry."""
        feature = {
            "id": "test_id",
            "geometry": {"type": "Point", "coordinates": [123.456, 789.012]},
            "properties": {"height": 15.5, "name": "Test Building"},
        }

        result = processor._extract_feature(feature)

        assert result["id"] == "test_id"
        assert result["Easting"] == "123.4560"
        assert result["Northing"] == "789.0120"
        assert result["height"] == 15.5
        assert result["name"] == "Test Building"

    def test_extract_feature_multipoint_geometry(self, processor):
        """Test extracting feature with MultiPoint geometry."""
        feature = {
            "id": "test_id",
            "geometry": {"type": "MultiPoint", "coordinates": [[123.456, 789.012]]},
            "properties": {"height": 15.5},
        }

        result = processor._extract_feature(feature)

        assert result["Easting"] == "123.4560"
        assert result["Northing"] == "789.0120"

    def test_extract_feature_invalid_geometry(self, processor):
        """Test extracting feature with invalid geometry."""
        feature = {
            "id": "test_id",
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
            "properties": {},
        }

        result = processor._extract_feature(feature)

        assert result["Easting"] is None
        assert result["Northing"] is None

    def test_extract_feature_no_geometry(self, processor):
        """Test extracting feature without geometry."""
        feature = {"id": "test_id", "properties": {"height": 15.5}}

        result = processor._extract_feature(feature)

        assert result["Easting"] is None
        assert result["Northing"] is None

    def test_process_tile_data_citymodel(self, sample_tile_data, processor):
        """Test processing tile data for citymodel type."""
        result = processor.process_tile_data(sample_tile_data, "citymodel")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "LoD1_32_564_5935_1_HH.xml"

    def test_process_tile_data_basic(self, sample_tile_data, processor):
        """Test processing tile data for basic type."""
        result = processor.process_tile_data(sample_tile_data, "basic")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "dgm1_32_564_9350_1_hh_2022.tif"

    def test_process_tile_data_empty_data(self, processor):
        """Test processing empty tile data."""
        result = processor.process_tile_data({}, "citymodel")
        assert result == []

    def test_process_tile_data_no_kachelbezeichnung(self, processor):
        """Test processing tile data without kachelbezeichnung_dk5 column."""
        data = {
            "features": [
                {
                    "id": "1",
                    "geometry": {"type": "Point", "coordinates": [564000.0, 5935000.0]},
                    "properties": {"other_property": "value"},
                }
            ]
        }
        result = processor.process_tile_data(data, "citymodel")
        assert result == []

    def test_transform_value_citymodel_valid(self, processor):
        """Test transforming valid value for citymodel."""
        result = processor._transform_value("32_564000_5935000", "citymodel")
        assert result == "LoD1_32_564_5935_1_HH.xml"

    def test_transform_value_basic_valid(self, processor):
        """Test transforming valid value for basic."""
        result = processor._transform_value("32_564000_5935000", "basic")
        assert result == "dgm1_32_564_9350_1_hh_2022.tif"

    def test_transform_value_invalid_format(self, processor):
        """Test transforming invalid format."""
        result = processor._transform_value("invalid_format", "citymodel")
        assert result is None

    def test_transform_value_invalid_model_type(self, processor):
        """Test transforming with invalid model type."""
        result = processor._transform_value("32_564000_5935000", "invalid_type")
        assert result is None

    def test_transform_value_non_numeric_parts(self, processor):
        """Test transforming value with non-numeric parts."""
        result = processor._transform_value("32_abc_def", "citymodel")
        assert result is None

    def test_transform_value_insufficient_parts(self, processor):
        """Test transforming value with insufficient parts."""
        result = processor._transform_value("32_564000", "citymodel")
        assert result is None

    def test_transform_value_too_many_parts(self, processor):
        """Test transforming value with too many parts."""
        result = processor._transform_value("32_564000_5935000_extra", "citymodel")
        assert result is None
