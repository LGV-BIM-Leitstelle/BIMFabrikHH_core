from functools import partial
from math import pi
from typing import Dict, Optional

from BIMFabrikHH.core.geom_base_point import BasePoint
from pandas import to_numeric

from ...core.ifc_modelbuilder import IfcModelBuilder
from ...core.ifc_utils import IfcFileCreator
from ...core.math_operations import MathTool
from ...core.ogc_values_extractor import extract_project_info, extract_level_of_geometry, extract_psets_basepoint
from ...core.request_oaf import HamburgOGCAPI
from ...default.url_api import PathUrl
from ...pydantic_models.params_bbox import BoundingBoxParams
from ...pydantic_models.params_tree import RequestParams
from .baum_col_names import DfColTree
from .baum_manager import BaumManager


class BaumModeller:

    def __init__(self):
        self.baum_manager = BaumManager()
        self.builder = IfcModelBuilder()
        self.model = None

    @staticmethod
    def get_oaf_trees(bbox, skip_geometry=False):

        url = PathUrl.URL_OAF_TREES

        tree_properties = (
            "gid, baumid, baumnummer, gattung_deutsch, art_deutsch, sorte_deutsch, pflanzjahr, kronendurchmesser, "
            "stammumfang, strasse, stadtteil, bezirk",
        )

        params_trees = {
            "f": "json",
            "bbox": f"{bbox.min_x},{bbox.min_y},{bbox.max_x},{bbox.max_y}",
            "crs": "http://www.opengis.net/def/crs/EPSG/0/25832",
            "limit": 2000,
            "properties": tree_properties,
            "skipGeometry": str(skip_geometry).lower(),
        }

        trees_data: Dict = HamburgOGCAPI.fetch_data(url, params_trees)

        return trees_data

    @staticmethod
    def get_oaf_tree_df(x1, y1, x2, y2):
        """Get OAF tree data as a DataFrame for the given bounding box coordinates."""

        bbox = BoundingBoxParams(min_x=x1, min_y=y1, max_x=x2, max_y=y2)

        url = PathUrl.URL_OAF_TREES

        tree_properties = (
            "gid, baumid, baumnummer, gattung_deutsch, art_deutsch, sorte_deutsch, pflanzjahr, kronendurchmesser, "
            "stammumfang, strasse, stadtteil, bezirk"
        )

        params_trees = {
            "f": "json",
            "bbox": f"{bbox.min_x},{bbox.min_y},{bbox.max_x},{bbox.max_y}",
            "crs": "http://www.opengis.net/def/crs/EPSG/0/25832",
            "limit": 2000,
            "properties": tree_properties,
            "skipGeometry": "false",
        }

        tree_data: Dict = HamburgOGCAPI.fetch_data(url, params_trees)

        df = HamburgOGCAPI.data_to_dataframe(tree_data)

        df[DfColTree.STAMMUMFANG_BK] = BaumModeller.convert_umfang_durchmesser(
            df, DfColTree.STAMMUMFANG_BK, MathTool.float_4f
        )

        return df

    @staticmethod
    def convert_umfang_durchmesser(df, col_name, formatting_function):
        """
        Args:
            df (pd.DataFrame): The DataFrame containing the column to process.
            col_name (str): The name of the column to process.
            formatting_function (function): The formatting function to apply to the processed values.

        Returns:
            pd.Series: The processed column.
        """

        # Convert to numeric first (coercing errors to NaN), then divide by 100
        df[col_name] = to_numeric(df[col_name], errors="coerce") / 100

        df[col_name] /= pi

        # Diameter will be set 0.05 for diameter lower than 0.05
        df[col_name] = df[col_name].apply(lambda x: 0.05 if x < 0.05 else x)

        df[col_name] = df[col_name].apply(partial(formatting_function))

        return df[col_name]

    def create_tree_model(self, model_params: RequestParams) -> Optional[bytes]:
        """
        Create trees from a given ModelParams, which includes the bounding box and other parameters.
        This method handles filtering trees within the bounding box and creating the IFC model.

        Args:
            model_params: Parameters for the model including bounding box and project info

        Returns:
            IFC model as bytes or None if creation fails
        """
        x1 = model_params.bbox.min_x
        y1 = model_params.bbox.min_y
        x2 = model_params.bbox.max_x
        y2 = model_params.bbox.max_y

        df = self.get_oaf_tree_df(x1, y1, x2, y2)

        if df.empty:
            print("No valid tree data found within the bounding box")
            return None

        self.builder.reset_model()

        project_name, site_name, building_name = extract_project_info(model_params.containers)
        level_of_geom = extract_level_of_geometry(model_params.containers)

        self.builder.build_project(project_name=project_name, site_name=site_name, building_name=building_name)

        self.model = self.builder.get_model()
        if not self.model:
            print("Model not initialized")
            return None

        self.baum_manager.place_trees_from_df(self.model, df, level_of_geom, self.builder.site, self.builder.body)

        # create project base point
        first_point = df["Easting"].iloc[0], df["Northing"].iloc[0]
        x, y = first_point
        pset_groups = extract_psets_basepoint(model_params.containers)
        bp_creator = BasePoint(self.model, self.builder.body, self.builder.site)
        bp_creator.create_base_point(size=1.0, x=x, y=y, pset_groups=pset_groups)

        print("Saving IFC model to memory...")

        return IfcFileCreator.save_ifc_in_memory(self.model)
