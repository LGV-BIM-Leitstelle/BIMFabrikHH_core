"""
Applications Package

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
Applications for BIMFabrikHH.

This module contains the main application classes for different types of
geospatial data processing: trees, digital terrain models, city models, and basepoints.
"""

# Basepoint applications
from .basepoint.basic.app import BasepointBasicApp

# City model applications
from .city.app import CityGMLParser

# Terrain applications
from .terrain.basic import create_combined_terrain_ifc, process_terrain_folder_to_ifc

# Tree applications
from .trees.basic.app import BaumModeller

__all__ = [
    # Basepoint applications
    "BasepointBasicApp",
    # City model applications
    "CityGMLParser",
    # Terrain applications
    "process_terrain_folder_to_ifc",
    "create_combined_terrain_ifc",
    # Tree applications
    "BaumModeller",
]
