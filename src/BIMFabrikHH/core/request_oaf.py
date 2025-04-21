import logging

import pandas as pd
import requests
from BIMFabrikHH.core.math_operations import MathTool
from BIMFabrikHH.default.url_api import PathUrl


class HamburgOGCAPI:

    @staticmethod
    def fetch_data(base_url: str, params: dict) -> dict | None:
        """
        Fetch data from the given API endpoint.

        Args:
            base_url (str): API base URL.
            params (dict): API request parameters.

        Returns:
            dict | None: Parsed JSON response if successful, otherwise None.
        """

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            return data

        except requests.exceptions.RequestException as e:
            print(f"Error fetching data from {base_url}: {e}")
            return None

    @staticmethod
    def data_to_dataframe(data: dict) -> pd.DataFrame:
        """
        Convert API response data to a Pandas DataFrame.

        Args:
            data (dict): API response data containing features.

        Returns:
            pd.DataFrame: DataFrame containing extracted features.
        """

        if not data or "features" not in data:
            logging.warning("No valid data found in response")
            return pd.DataFrame()

        features = [HamburgOGCAPI._extract_feature(f) for f in data["features"]]

        df = pd.DataFrame(features)
        if df.empty:
            logging.warning("No valid features found")

        return df

    @staticmethod
    def get_tiles(x1: float, y1: float, x2: float, y2: float) -> list[str]:
        """
        Fetch tile names within a specified bounding box.

        Args:
            x1 (float): Minimum X (Easting).
            y1 (float): Minimum Y (Northing).
            x2 (float): Maximum X (Easting).
            y2 (float): Maximum Y (Northing).

        Returns:
            list[str]: List of transformed tile names.
        """

        params = {
            "f": "json",
            "bbox": f"{x1},{y1},{x2},{y2}",
            "skipGeometry": "false",
        }

        data = HamburgOGCAPI.fetch_data(PathUrl.URL_OAF_TILES_DGM, params)

        df = HamburgOGCAPI.data_to_dataframe(data)

        if df.empty or "kachelbezeichnung_dk5" not in df:
            return []

        df["kachelbezeichnung_dk5"] = df["kachelbezeichnung_dk5"].apply(HamburgOGCAPI._transform_value)

        return df["kachelbezeichnung_dk5"].dropna().tolist()

    # @staticmethod
    # def _extract_feature(feature: dict) -> dict:
    #     """
    #     Extract relevant data from a single feature.
    #
    #     Args:
    #         feature (dict): A single feature from the API response.
    #
    #     Returns:
    #         dict: Processed feature data with coordinates and properties.
    #     """
    #
    #     geometry = feature.get("geometry", {})
    #     coords = geometry.get("coordinates", [])
    #     x, y = (None, None)
    #
    #     if geometry.get("type") in ["Point", "MultiPoint"] and len(coords) >= 2:
    #         x, y = MathTool.float_4f(coords[0]), MathTool.float_4f(coords[1])
    #
    #     return {"id": feature.get("id"), "Easting": x, "Northing": y, **feature.get("properties", {})}

    @staticmethod
    def _extract_feature(feature: dict) -> dict:
        """
        Extract relevant data from a single feature.

        Args:
            feature (dict): A single feature from the API response.

        Returns:
            dict: Processed feature data with coordinates and properties.
        """
        geometry = feature.get("geometry", {})
        coords = geometry.get("coordinates", [])
        x, y = (None, None)

        if geometry.get("type") == "Point" and len(coords) == 2:
            x, y = MathTool.float_4f(coords[0]), MathTool.float_4f(coords[1])
        elif geometry.get("type") == "MultiPoint" and len(coords) > 0 and len(coords[0]) == 2:
            x, y = MathTool.float_4f(coords[0][0]), MathTool.float_4f(coords[0][1])

        return {
                "id": feature.get("id"),
                "Easting": x,
                "Northing": y,
                **feature.get("properties", {})
        }


    @staticmethod
    def _transform_value(value: str) -> str | None:
        """
        Transform raw tile name into city model filename format.

        Args:
            value (str): Raw tile name (e.g., "DK5_565000_5932000").

        Returns:
            str | None: Transformed filename or None if format invalid.
        """

        parts = value.split("_")
        # Ensure the format is as expected
        if len(parts) != 3:
            return None

        first_part = "LoD1_32"
        # Convert 565000 → 565
        second_part = str(int(parts[1]) // 1000)

        # Extract last 4 digits correctly (5932000 → 5932)
        third_part = str((int(parts[2]) // 1000) % 10000)

        suffix = "1_HH.xml"
        citymodell_filename = f"{first_part}_{second_part}_{third_part}_{suffix}"

        return citymodell_filename
