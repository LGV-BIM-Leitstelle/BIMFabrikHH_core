from functools import partial
from math import pi
from pathlib import Path
from typing import Optional

import pandas as pd

from ....core.data_processing.data_processor import DataProcessor
from ....core.geometry.basepoint_objects import BasePointNorth
from ....core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from ....core.georeferencing.extract_elevation import extract_elevation_df_from_geotiff
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_utils import IfcFileCreator
from ....core.ogc_values_extractor import extract_level_of_geometry, extract_project_info, extract_psets_basepoint
from ....data_models.params_tree import RequestParams
from ....default_data.paths import PathConfig
from ....utils.math_operations import MathTool
from .baum_col_names import DfColTree
from .baum_manager import BaumManager


class BaumModeller:
    """
    Main class for creating IFC tree models from raw or tabular tree data.
    Handles conversion, processing, and model building for tree data.
    """

    def __init__(self):
        """
        Initialize the BaumModeller with a BaumManager and IfcModelBuilder.
        """
        self.baum_manager = BaumManager()
        self.builder = IfcModelBuilder()
        self.model = None

    @staticmethod
    def raw_data_to_tree_df(raw_tree_data: dict) -> "pd.DataFrame":
        """
        Convert raw tree data (dict) to a pandas DataFrame using processing logic.

        Args:
            raw_tree_data (dict): Raw tree data, typically from an API or file.

        Returns:
            pd.DataFrame: DataFrame with processed tree data.
        """
        df = DataProcessor.raw_data_to_dataframe(raw_tree_data)
        # If the expected column exists, convert circumference to diameter
        if not df.empty and DfColTree.STAMMUMFANG_BK in df:
            df[DfColTree.STAMMUMFANG_BK] = BaumModeller.convert_umfang_durchmesser(
                df, DfColTree.STAMMUMFANG_BK, MathTool.float_4f
            )
        return df

    @staticmethod
    def convert_umfang_durchmesser(df, col_name, formatting_function):
        """
        Convert circumference to diameter and apply formatting.

        Args:
            df (pd.DataFrame): The DataFrame containing the column to process.
            col_name (str): The name of the column to process.
            formatting_function (function): The formatting function to apply to the processed values.

        Returns:
            pd.Series: The processed column.
        """
        # Convert to numeric first (coercing errors to NaN), then divide by 100 to get meters
        df[col_name] = pd.to_numeric(df[col_name], errors="coerce") / 100
        df[col_name] /= pi  # Convert circumference to diameter
        # Diameter will be set 0.05 for diameter lower than 0.05
        df[col_name] = df[col_name].apply(lambda x: 0.05 if x < 0.05 else x)
        df[col_name] = df[col_name].apply(partial(formatting_function))
        return df[col_name]

    def create_tree_model_from_df(
        self, df, model_params: RequestParams, tif_path: Optional[str] = None
    ) -> Optional[Path]:
        """
        Create trees from a DataFrame and model parameters.

        Args:
            df (pd.DataFrame): DataFrame containing tree data.
            model_params (RequestParams): Request parameters for the model.
            tif_path (Optional[str]): Path to the GeoTIFF file for elevation extraction.
            If None, elevation is not extracted.

        Returns:
            Optional[Path]: Path to the saved IFC file if successful, None if failed.

        Raises:
            IOError: If there are issues saving the IFC model.
        """
        if df.empty:
            print("No valid tree data found within the bounding box")
            return None

        # Optionally extract elevation from GeoTIFF
        if tif_path is not None:
            df = extract_elevation_df_from_geotiff(
                df, tif_path, DfColTree.EASTING, DfColTree.NORTHING, DfColTree.ELEVATION
            )

        try:
            self.builder.reset_model()
            # Extract project and geometry info from model parameters
            project_name, site_name, building_name = extract_project_info(model_params.containers)
            level_of_geom = extract_level_of_geometry(model_params.containers)
            self.builder.build_project(project_name=project_name, site_name=site_name, building_name=building_name)
            self.model = self.builder.get_model()

            if not self.model:
                print("Model not initialized")
                return None

            # Place trees in the IFC model using the BaumManager
            self.baum_manager.place_trees_from_df(self.model, df, level_of_geom, self.builder.site, self.builder.body)

            # Create project base point using the lower-left of the bbox (after conversion to EPSG:25832)
            bbox_wgs84 = (
                model_params.bbox.min_x,
                model_params.bbox.min_y,
                model_params.bbox.max_x,
                model_params.bbox.max_y,
            )
            bbox = bbox_wgs84_to_epsg25832(bbox_wgs84)
            x, y = bbox[0], bbox[1]
            pset_groups = extract_psets_basepoint(model_params.containers)
            # Create basepoint data for the new interface
            basepoint_data = {"position": (x, y, 0), "size": 1.0, "psets": pset_groups}
            basepoint = BasePointNorth.from_basepoint_data(basepoint_data)
            basepoint_entity = basepoint.as_product(self.model, self.builder)
            # Assign to site (or storey as fallback)
            import ifcopenshell.api.spatial as spatial

            if self.builder.site:
                spatial.assign_container(self.model, relating_structure=self.builder.site, products=[basepoint_entity])
            else:
                # Create a storey as fallback
                import ifcopenshell.api.root as root

                storey = root.create_entity(self.model, ifc_class="IfcBuildingStorey", name="Default Storey")
                spatial.assign_container(self.model, relating_structure=storey, products=[basepoint_entity])

            output_file = PathConfig.OUTPUT / "output_baum.ifc"
            file_path = IfcFileCreator.save_ifc_file(self.model, str(output_file))
            print(f"IFC file saved to: {file_path}")
            return file_path

        except IOError as e:
            print(f"Error saving IFC model: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error creating tree model: {e}")
            return None

    def create_tree_model(
        self, raw_tree_data: dict, model_params: RequestParams, tif_path: Optional[str] = None
    ) -> Optional[Path]:
        """
        Convenience method: Accepts raw tree data (dict), processes it, and creates IFC model.

        Args:
            raw_tree_data (dict): Raw tree data, typically from an API or file.
            model_params (RequestParams): Request parameters for the model.
            tif_path (Optional[str]): Path to the GeoTIFF file for elevation extraction.
            If None, elevation is not extracted.

        Returns:
            Optional[Path]: Path to the saved IFC file if successful, None if failed.
        """
        df = self.raw_data_to_tree_df(raw_tree_data)
        return self.create_tree_model_from_df(df, model_params, tif_path)
