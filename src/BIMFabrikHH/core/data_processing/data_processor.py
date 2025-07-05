import logging
from typing import List, Optional

import pandas as pd

from ...utils.math_operations import MathTool


class DataProcessor:
    """
    Pure data processing functions moved from HamburgOGCAPI.
    Provides static methods for converting and transforming API and tile data.
    """

    @staticmethod
    def raw_data_to_dataframe(data: dict) -> pd.DataFrame:
        """
        Convert API response data to a Pandas DataFrame.

        Args:
            data (dict): API response data containing 'features'.

        Returns:
            pd.DataFrame: DataFrame with extracted features, or empty if invalid.
        """
        if not data or "features" not in data:
            logging.warning("No valid data found in response")
            return pd.DataFrame()
        features = [DataProcessor._extract_feature(f) for f in data["features"]]
        df = pd.DataFrame(features)
        if df.empty:
            logging.warning("No valid features found")
        return df

    @staticmethod
    def _extract_feature(feature: dict) -> dict:
        """
        Extract relevant data from a single feature.

        Args:
            feature (dict): Feature dictionary from API response.

        Returns:
            dict: Dictionary with id, Easting, Northing, and properties.
        """
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])
        x, y = (None, None)
        # Handle Point and MultiPoint geometries
        if geometry.get("type") == "Point" and len(coords) == 2:
            x, y = MathTool.float_4f(coords[0]), MathTool.float_4f(coords[1])
        elif geometry.get("type") == "MultiPoint" and len(coords) > 0 and len(coords[0]) == 2:
            x, y = MathTool.float_4f(coords[0][0]), MathTool.float_4f(coords[0][1])
        return {
            "id": feature.get("id"),
            "Easting": x,
            "Northing": y,
            **feature.get("properties", {}),
        }

    @staticmethod
    def process_tile_data(raw_tile_data: dict, model_type: str = "citymodel") -> List[str]:
        """
        Process raw tile data to get transformed tile names.

        Args:
            raw_tile_data (dict): Raw tile data from API.
            model_type (str): Type of model ('citymodel' or 'basic').

        Returns:
            List[str]: List of transformed tile filenames.
        """
        df = DataProcessor.raw_data_to_dataframe(raw_tile_data)
        if df.empty or "kachelbezeichnung_dk5" not in df:
            return []
        df["kachelbezeichnung_dk5"] = df["kachelbezeichnung_dk5"].apply(
            lambda val: DataProcessor._transform_value(val, model_type)
        )
        return df["kachelbezeichnung_dk5"].dropna().tolist()

    @staticmethod
    def _transform_value(value: str, model_type: str = "citymodel") -> Optional[str]:
        """
        Transform raw tile name into appropriate filename format for a given model type.

        Args:
            value (str): Raw tile name string.
            model_type (str): Type of model ('citymodel' or 'basic').

        Returns:
            Optional[str]: Transformed filename or None if invalid.
        """
        parts = value.split("_")
        if len(parts) != 3:
            return None
        try:
            x = int(parts[1]) // 1000
            if model_type == "citymodel":
                y = int(parts[2]) // 1000  # 5932000 → 5932
                return f"LoD1_32_{x}_{y}_1_HH.xml"
            elif model_type == "basic":
                y = (int(parts[2]) // 100) % 10000  # 5932000 → 9320
                return f"dgm1_32_{x}_{y}_1_hh_2022.tif"
            else:
                return None
        except ValueError:
            return None
