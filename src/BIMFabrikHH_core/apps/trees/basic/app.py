"""
Basic Trees Application

Copyright (C) 2025 Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung
BIM-Leitstelle, Ahmed Salem <ahmed.salem@gv.hamburg.de>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

from functools import partial
from math import pi
from pathlib import Path
from typing import Optional

import ifcopenshell.util.placement
import pandas as pd
from ifcfactory import BIMFactoryElement, Transform

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.data_processing.data_processor import DataProcessor
from BIMFabrikHH_core.core.geometry.advanced_objects import create_basepoint_quad
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.georeferencing.extract_elevation import extract_elevation_df_from_geotiff
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import (
    extract_level_of_geometry,
    extract_project_info,
    extract_psets_basepoint,
)
from BIMFabrikHH_core.core.utils import MathTool
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

from .baum_col_names import DfColTree
from .baum_manager import BaumManager

logger = get_level_logger("trees_basic_app")


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
    def get_oaf_tree_df(x1: float, y1: float, x2: float, y2: float) -> "pd.DataFrame":
        """
        Fetch tree data from OAF API and convert to DataFrame.

        Args:
            x1 (float): Minimum X coordinate
            y1 (float): Minimum Y coordinate
            x2 (float): Maximum X coordinate
            y2 (float): Maximum Y coordinate

        Returns:
            pd.DataFrame: DataFrame with tree data from OAF API
        """
        try:
            from BIMFabrikHH_intern.core.http_requests_pro import DataFetcher

            bbox = {
                "min_x": x1,
                "min_y": y1,
                "max_x": x2,
                "max_y": y2,
            }

            raw_tree_data = DataFetcher.fetch_tree_data(bbox)
            return BaumModeller.raw_data_to_tree_df(raw_tree_data)
        except Exception as e:
            logger.error(f"Failed to fetch tree data from OAF API: {e}")
            return pd.DataFrame()

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
        self,
        df,
        model_params: RequestParams,
        tif_path: Optional[str] = None,
        use_geotiff_elevation: bool = True,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Create trees from a DataFrame and model parameters.

        Args:
            df (pd.DataFrame): DataFrame containing tree data.
            model_params (RequestParams): Request parameters for the model.
            tif_path (Optional[str]): Path or URL to the GeoTIFF file for elevation extraction.
                If None, elevation is not extracted.
            use_geotiff_elevation (bool): If True, extract elevation from GeoTIFF file.
                If False, skip elevation extraction. Default is True.
            output_path (Optional[Path]): Full path where to save the IFC file.
                If provided, the parent directory must exist. If None, saves to default location.

        Returns:
            Optional[Path]: Path to the saved IFC file if successful, None if failed.

        Raises:
            IOError: If there are issues saving the IFC model.
            FileNotFoundError: If output_path is provided but its parent directory doesn't exist.
        """

        if df.empty:
            logger.warning("No valid tree data found within the bounding box")
            return None

        # Optionally extract elevation from GeoTIFF
        if tif_path is not None and use_geotiff_elevation:
            df = extract_elevation_df_from_geotiff(
                df, tif_path, DfColTree.EASTING, DfColTree.NORTHING, DfColTree.ELEVATION
            )

        try:
            self.builder.reset_model()
            # Extract project and geometry info from model parameters
            project_name, site_name, building_name = extract_project_info(model_params.containers)
            level_of_geom = extract_level_of_geometry(model_params.containers)
            self.builder.build_project(
                project_name=project_name,
                coordinate_system=CoordinateSystemTemplates.epsg_25832(),
                coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
                site_name=site_name,
                building_name=building_name,
            )
            self.model = self.builder.model

            if not self.model:
                logger.warning("Model not initialized")
                return None

            # Create shape builder after model is built
            builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.model)

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
            # Create basepoint using new BIMFactoryElement pattern
            basepoint_entity = BIMFactoryElement(
                inst=self.builder.site,
                children=[
                    Transform(
                        vec=(x, y, 0),
                        item=create_basepoint_quad(size=1.0, psets=pset_groups),
                    ),
                ],
            ).build(self.model)

            # Save IFC file
            file_path = self.builder.save_ifc_to_output("output_baum.ifc", output_path=output_path)

            return file_path

        except IOError as e:
            logger.error(f"Error saving IFC model: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating tree model: {e}")
            return None

    def create_tree_model(
        self,
        raw_tree_data: dict,
        model_params: RequestParams,
        tif_path: Optional[str] = None,
        use_geotiff_elevation: bool = True,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """
        Convenience method: Accepts raw tree data (dict), processes it, and creates IFC model.

        Args:
            raw_tree_data (dict): Raw tree data, typically from an API or file.
            model_params (RequestParams): Request parameters for the model.
            tif_path (Optional[str]): Path or URL to the GeoTIFF file for elevation extraction.
                If None, elevation is not extracted.
            use_geotiff_elevation (bool): If True, extract elevation from GeoTIFF file.
                If False, skip elevation extraction. Default is True.
            output_path (Optional[Path]): Full path where to save the IFC file.
                If provided, the parent directory must exist. If None, saves to default location.

        Returns:
            Optional[Path]: Path to the saved IFC file if successful, None if failed.
        """
        df = self.raw_data_to_tree_df(raw_tree_data)
        return self.create_tree_model_from_df(df, model_params, tif_path, use_geotiff_elevation, output_path)
