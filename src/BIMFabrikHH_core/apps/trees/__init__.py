"""
Trees Package

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
Tree modeling application for BIMFabrikHH.

This module contains functionality for processing tree data from Hamburg's
OGC API and converting it to IFC format.
"""

from .basic.app import BaumModeller
from .basic.baum_col_names import DfColTree
from .basic.baum_manager import BaumManager

__all__ = [
    "BaumModeller",
    "BaumManager",
    "DfColTree",
]
