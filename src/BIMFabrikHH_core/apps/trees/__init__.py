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
Tree modeling applications for BIMFabrikHH.

Two record-builder apps share the same ``TreeRecord`` input contract:

- :class:`TreesBasicApp` — **deprecated**; use :class:`TreesGenericApp`
  or :class:`TreesRustApp`.
  Mesh trunk + icosphere crown via ``ifcopenshell.api``.
- :class:`TreesGenericApp` — ``ifcfactory.BIMFactoryElement`` pipeline.
- :class:`TreesRustApp` — ``bimfabrikhh_core_rs.trees_to_ifc`` (same ``TreeRecord`` list).

Data-processing helpers live in :mod:`BIMFabrikHH_core.apps.trees.processing`
(DataFrame → list[TreeRecord] with psets; height rules; validation).
"""

from BIMFabrikHH_core.data_models import TreeRecord

from .basic.app import TreesBasicApp
from .column_schema import BAUMKATASTER_SCHEMA, DEFAULT_OAF_SCHEMA, TreeColumnSchema
from .generic.app import TreesGenericApp
from .generic_rust import TreesRustApp
from .processing import (
    TreeDimensions,
    build_tree_psets,
    calculate_tree_height,
    collect_pydantic_psets,
    dataframe_to_records,
    resolve_tree_dimensions,
    tree_crown_detail_from_containers,
    validate_tree_records,
)

__all__ = [
    "BAUMKATASTER_SCHEMA",
    "DEFAULT_OAF_SCHEMA",
    "TreeColumnSchema",
    "TreeDimensions",
    "TreeRecord",
    "TreesBasicApp",
    "TreesGenericApp",
    "TreesRustApp",
    "build_tree_psets",
    "calculate_tree_height",
    "collect_pydantic_psets",
    "dataframe_to_records",
    "resolve_tree_dimensions",
    "tree_crown_detail_from_containers",
    "validate_tree_records",
]
