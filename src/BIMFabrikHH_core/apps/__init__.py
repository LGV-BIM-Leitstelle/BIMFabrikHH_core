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

# Borehole applications
from .boreholes.generic.app import BoreholesGenericApp

# City model applications
from .city.basic.app import CityBasicApp
from .city.generic.app import CityGenericApp
from .city.parser import CityGMLParser

# Terrain applications
from .terrain.basic.app import TerrainBasicApp
from .terrain.generic.app import TerrainGenericApp

# Tree applications
from .trees.basic.app import TreesBasicApp
from .trees.generic.app import TreesGenericApp

__all__ = [
    # Basepoint applications
    "BasepointBasicApp",
    # Borehole applications
    "BoreholesGenericApp",
    # City model applications
    "CityBasicApp",
    "CityGenericApp",
    "CityGMLParser",
    # Terrain applications
    "TerrainBasicApp",
    "TerrainGenericApp",
    # Tree applications
    "TreesBasicApp",
    "TreesGenericApp",
]
