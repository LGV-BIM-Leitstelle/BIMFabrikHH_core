"""
BIMFabrikHH - Hamburg BIM Factory

A Python package for converting geospatial data to IFC format.
Part of the Connected Urban Twins (CUT) project by the City of Hamburg.
"""

__version__ = "0.1.0"
__author__ = "Ahmed Salem <ahmed.salem@gv.hamburg.de>"
__description__ = "Hamburg BIM Factory for geospatial data to IFC conversion"

from .apps.city_model.app import CityGMLParser, process_gml_to_ifc
from .apps.terrain.basic import create_combined_terrain_ifc, process_terrain_folder_to_ifc

# App imports
from .apps.trees.basic.app import BaumModeller

# Core imports
from .core.geom_base_point import BasePoint
from .core.geometry_creator import GeometryCreator
from .core.ifc_modelbuilder import IfcModelBuilder
from .core.ifc_utils import IfcFileCreator

# Pydantic models
from .data_models.params_bbox import BoundingBoxParams
from .data_models.params_tree import Component, Container, RequestParams

# Default configurations
from .default_data.paths import PathConfig
from .utils.math_operations import MathTool

__all__ = [
    # Core functionality
    "IfcModelBuilder",
    "IfcFileCreator",
    "GeometryCreator",
    "BasePoint",
    "MathTool",
    # Applications
    "BaumModeller",
    "process_terrain_folder_to_ifc",
    "create_combined_terrain_ifc",
    "process_gml_to_ifc",
    "CityGMLParser",
    # Data models
    "BoundingBoxParams",
    "RequestParams",
    "Container",
    "Component",
    # Configuration
    "PathConfig",
]
