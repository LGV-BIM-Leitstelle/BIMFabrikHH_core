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
    Product,
    Rect,
    Representation,
    Sphere,
    Translate,
    profile,
)
from .tree_objects import Crown, Tree, TreeCluster, Trunk

__all__ = [
    # Generic geometry
    "Box",
    "Cube",
    "Rect",
    "Extrusion",
    "Translate",
    "Representation",
    "Product",
    "MeshRepresentation",
    "Cylinder",
    "Sphere",
    "profile",
    # Tree-specific
    "Tree",
    "Trunk",
    "Crown",
    "TreeCluster",
    # Basepoint-specific
    "BasePoint",
    "BasePointNorth",
]
