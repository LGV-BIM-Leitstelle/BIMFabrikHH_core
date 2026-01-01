import logging
from typing import Optional

import pandas as pd

from BIMFabrikHH_core.core.utils.math_operations import MathTool


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

    @staticmethod
    def create_df_from_excel(excel_file_path: str) -> pd.DataFrame:
        """
        Create a DataFrame from an Excel file.

        Args:
            excel_file_path (str): Path to the Excel file.

        Returns:
            pd.DataFrame: DataFrame loaded from the Excel file.
        """
        df = pd.read_excel(excel_file_path)
        return df

    @staticmethod
    def get_column_value(
        df: pd.DataFrame, condition_col: str, condition_val: any, target_col: str, default: str = "None"
    ) -> str:
        """
        Retrieve the first match for a target column based on a condition, or return a default_data value.

        Args:
            df (pd.DataFrame): The DataFrame to search.
            condition_col (str): The column name to apply the condition on.
            condition_val: The value to match in the condition column.
            target_col (str): The column name to retrieve the value from.
            default (str): The default_data value to return if no match is found.

        Returns:
            str: The matched value or the default_data value.
        """
        match = df.loc[df[condition_col] == condition_val, target_col]
        if not match.empty:
            return match.iloc[0]
        return default

    @staticmethod
    def process_tile_data(data: dict, model_type: str = "citymodel") -> list:
        """
        Process tile data and return a list of filenames.

        Args:
            data (dict): Tile data containing features.
            model_type (str): Type of model ('citymodel' or 'basic').

        Returns:
            list: List of processed filenames.
        """
        if not data or "features" not in data:
            return []

        filenames = []
        for feature in data["features"]:
            properties = feature.get("properties", {})
            kachelbezeichnung = properties.get("kachelbezeichnung_dk5")
            if kachelbezeichnung:
                filename = DataProcessor._transform_value(kachelbezeichnung, model_type)
                if filename:
                    filenames.append(filename)

        return filenames
