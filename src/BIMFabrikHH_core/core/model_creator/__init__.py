"""
IFC Model Creator Module

This module provides classes and utilities for creating and managing IFC models.
It includes the main model builder class and utility methods for IFC operations.
"""

# IFC utilities
from . import ifc_utils as root

# Core model creation classes
from .ifc_modelbuilder import IfcModelBuilder
from .ifc_utils import IfcModelMethods, validate_ifc
from .project_init import georeference_options, init_ifc_project, output_coordinate_system

# Property set utilities
from .pset_utils import assign_psets_to_element, extract_psets_from_row, psets_to_wire

# Export the main classes
__all__ = [
    "IfcModelBuilder",  # Main class for building IFC models with saving capabilities
    "IfcModelMethods",  # Utility methods for IFC model creation and management
    "validate_ifc",  # Run ifcopenshell.validate --rules on an exported IFC file
    "georeference_options",  # init_ifc_project CRS keywords from an output transformer
    "init_ifc_project",  # One-call builder + project/site/building setup
    "output_coordinate_system",  # IFC CRS from an output transformer (also for the Rust writers)
    # Property set utilities
    "assign_psets_to_element",
    "extract_psets_from_row",
    "psets_to_wire",  # Pset models -> typed {pset: {property: value}} for the Rust writers
    # IFC utilities
    "root",
]
