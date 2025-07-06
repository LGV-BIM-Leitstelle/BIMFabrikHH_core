"""
Geometry Module
==============

This module provides composable, dataclass-based geometry creation for IFC models.
It combines the generic geometry primitives with tree-specific implementations.

Main Classes:
- Box, Cube, Rect, Extrusion: Basic geometry primitives
- Translate, Representation, Product: Composable geometry operations
- Tree, Trunk, Crown, TreeCluster: Tree-specific geometry
- MeshRepresentation: Mesh geometry container
"""

from .basepoint_objects import BasePoint, BasePointNorth
from .primitive_objects import (
    Box,
    Cube,
    Cylinder,
    Extrusion,
    MeshRepresentation,
    Element,
    Rect,
    Sphere,
    Translate,
    Profile,
)
from .tree_objects import Crown, Tree, TreeCluster, Trunk

__all__ = [
    # Generic geometry
    "Box",
    "Cube",
    "Rect",
    "Extrusion",
    "Translate",
    "Element",
    "MeshRepresentation",
    "Cylinder",
    "Sphere",
    "Profile",
    # Tree-specific
    "Tree",
    "Trunk",
    "Crown",
    "TreeCluster",
    # Basepoint-specific
    "BasePoint",
    "BasePointNorth",
]
