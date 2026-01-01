"""
IFC Model Creator Module

This module provides classes and utilities for creating and managing IFC models.
It includes the main model builder class and utility methods for IFC operations.
"""

# IFC utilities
from . import ifc_utils as root

# Core model creation classes
from .ifc_modelbuilder import IfcModelBuilder
from .ifc_utils import IfcModelMethods

# Property set utilities
from .pset_utils import assign_psets_to_element, extract_psets_from_row

# Export the main classes
__all__ = [
    "IfcModelBuilder",  # Main class for building IFC models with saving capabilities
    "IfcModelMethods",  # Utility methods for IFC model creation and management
    # Property set utilities
    "assign_psets_to_element",
    "extract_psets_from_row",
    # IFC utilities
    "root",
]
