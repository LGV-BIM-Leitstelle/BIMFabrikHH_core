"""
Geometry Module for BIMFabrikHH
==============================

This module provides composable, dataclass-based geometry creation for IFC models.
It combines the generic geometry primitives with tree-specific implementations.

Main Classes:
- Box, Cube, Rect, Extrusion: Basic geometry primitives
- Transform, Representation, Product: Composable geometry operations
- Tree, Trunk, Crown, TreeCluster: Tree-specific geometry
- MeshRepresentation: Mesh geometry container
"""

# Import order matters to avoid circular dependencies
# Import in dependency order: primitives -> advanced -> basepoint -> tree

# Primitive objects (base layer - imported from ifcfactory)
from ifcfactory import (
    BIMFactoryElement,
    Boolean,
    BooleanOperationTypes,
    Box,
    Circle,
    Cube,
    Cylinder,
    ElementInterface,
    Ellipse,
    EllipticalCylinder,
    Extrusion,
    MeshRepresentation,
    NgonCylinder,
    Polygon,
    Profile,
    Rect,
    RepresentationItem,
    Sphere,
    Style,
    Transform,
)

# Advanced objects (depends on primitives)
from .advanced_objects import ProjectBasePointNorthMesh, ProjectBasePointNorthQuad

# Tree objects (depends on primitives)
from .tree_objects import Crown, Tree, TreeCluster, Trunk

__all__ = [
    "Box",
    "Cube",
    "Rect",
    "Extrusion",
    "Transform",
    "MeshRepresentation",
    "NgonCylinder",
    "Sphere",
    "Profile",
    "Circle",
    "Ellipse",
    "Polygon",
    "Cylinder",
    "EllipticalCylinder",
    "Style",
    "Boolean",
    "BooleanOperationTypes",
    "RepresentationItem",
    "ElementInterface",
    "BIMFactoryElement",
    "ProjectBasePointNorthMesh",
    "ProjectBasePointNorthQuad",
    "Tree",
    "Trunk",
    "Crown",
    "TreeCluster",
]
