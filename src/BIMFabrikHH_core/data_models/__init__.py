"""
Pydantic models for BIMFabrikHH.

This module contains all Pydantic models for data validation and configuration
management throughout the application.
"""

# Core parameter models
from .params_basepoint import BasepointParams
from .params_bbox import BoundingBoxParams
from .params_tree import Component, Container, RequestParams

# Georeferencing models
from .pydantic_georeferencing import (
    CoordinateSystem,
    CoordinateSystemTemplates,
    check_projected_epsg,
    check_source_epsg,
    check_vertical_epsg,
)

# Property set models
from .pydantic_psets_BIMHH import (
    Pset_Georeferenzierung,
    Pset_Hyperlink,
    Pset_Modellinformation,
    Pset_Objektinformation,
    default_bim_hamburg_hyperlink,
)

# City model attribute models
from .pydantic_psets_city_model import (
    CityModelAttributes,
    Pset_BIMFabrikHH_Quantities,
    Pset_Objektinformation_CityModel,
    TypedCityBuilding,
    city_attrs_to_pset,
)
from .pydantic_psets_terrain import Pset_Objektinformation_DGM

# App input records
from .terrain_mesh import TerrainMesh
from .tree_record import TreeRecord

__all__ = [
    # Core parameter models
    "BasepointParams",
    "BoundingBoxParams",
    "RequestParams",
    "Container",
    "Component",
    # App input records
    "TerrainMesh",
    "TreeRecord",
    # Georeferencing models
    "CoordinateSystem",
    "CoordinateSystemTemplates",
    "check_projected_epsg",
    "check_source_epsg",
    "check_vertical_epsg",
    # Property set models
    "Pset_Objektinformation",
    "Pset_Objektinformation_DGM",
    "Pset_Modellinformation",
    "Pset_Georeferenzierung",
    "Pset_Hyperlink",
    "default_bim_hamburg_hyperlink",
    # City model attribute models
    "CityModelAttributes",
    "Pset_BIMFabrikHH_Quantities",
    "Pset_Objektinformation_CityModel",
    "TypedCityBuilding",
    "city_attrs_to_pset",
]
