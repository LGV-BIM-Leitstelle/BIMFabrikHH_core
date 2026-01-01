"""
BIMFabrikHH - Hamburg BIM Factory

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

A Python package for converting geospatial data to IFC format.
Part of the Connected Urban Twins (CUT) project by the City of Hamburg.
"""

__version__ = "0.1.0"
__author__ = "Ahmed Salem <ahmed.salem@gv.hamburg.de>"
__description__ = "Hamburg BIM Factory for geospatial data to IFC conversion"

# Configuration and utility imports
from BIMFabrikHH_core.config.paths import PathConfig

# Core functionality imports
# from BIMFabrikHH_intern.core.geom_base_point import BasePoint
# from BIMFabrikHH_intern.core.geometry_creator_pro import GeometryCreator
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder, IfcModelMethods
from BIMFabrikHH_core.core.utils.math_operations import MathTool

# Application imports
from .apps.terrain.basic import create_combined_terrain_ifc, process_terrain_folder_to_ifc
from .apps.trees.basic.app import BaumModeller

# Data model imports
from .data_models.params_bbox import BoundingBoxParams
from .data_models.params_tree import Component, Container, RequestParams

__all__ = [
    # Core functionality
    "IfcModelBuilder",
    "IfcModelMethods",
    "MathTool",
    # Applications
    "BaumModeller",
    "process_terrain_folder_to_ifc",
    "create_combined_terrain_ifc",
    # Data models
    "BoundingBoxParams",
    "RequestParams",
    "Container",
    "Component",
    # Configuration
    "PathConfig",
]
