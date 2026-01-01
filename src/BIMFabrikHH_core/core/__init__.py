"""
Core Package

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

"""
Core functionality for BIMFabrikHH.

This module contains the core classes and functions for IFC model creation,
geometry processing, API communication, and data handling.
"""

# Core geometry and model creation imports
# from BIMFabrikHH_intern.core.geom_base_point import BasePoint
# from BIMFabrikHH_intern.core.geometry_creator_pro import GeometryCreator
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets

# OGC extractor imports
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import (
    extract_level_of_geometry,
    extract_project_info,
    extract_psets_basepoint,
)

# Utility imports
from BIMFabrikHH_core.core.utils.math_operations import MathTool

# Data processing imports
from .data_processing.data_processor import DataProcessor
from .model_creator import IfcModelBuilder, IfcModelMethods

__all__ = [
    # Core model creation
    "IfcModelBuilder",
    "IfcModelMethods",
    "IfcSnippets",
    # Data processing
    "DataProcessor",
    # OGC extractor
    "extract_project_info",
    "extract_level_of_geometry",
    "extract_psets_basepoint",
    # Utilities
    "MathTool",
]
