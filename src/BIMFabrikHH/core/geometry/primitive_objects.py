"""
Primitive Geometry Objects
=========================

This module contains the core primitive objects for composable geometry creation.
These dataclasses can be used to build complex geometry arrangements in a
declarative, composable way.
"""

from dataclasses import dataclass
from typing import List, Tuple

import ifcopenshell
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.root as root
import ifcopenshell.util.representation
import numpy as np
from icosphere import icosphere as icosphere_lib
import math


# 'trait' for 2d definitions
class profile:
    pass


@dataclass
class MeshPrimitive:
    """Base class for mesh-based primitives"""

    def create_ifc_mesh(self, model, body):
        """Create IFC mesh representation - shared by all mesh primitives"""
        vertices, faces = self.create_mesh()
        return ifcopenshell.api.geometry.add_mesh_representation(
            model, context=body, vertices=[vertices], faces=[faces]  # Wrap in list  # Wrap in list
        )


@dataclass
class Rect(profile):
    width: float
    height: float

    def build(self, model, builder):
        return builder.rectangle(size=(self.width, self.height))


@dataclass
class Extrusion:
    basis: profile
    depth: float

    def build(self, model, builder):
        builder.extrude(self.basis.build(model, builder), self.depth)


@dataclass
class Box:
    width: float
    depth: float
    height: float

    def build(self, model, builder):
        return Extrusion(Rect(self.width, self.depth), self.height).build(model, builder)


@dataclass
class Cube:
    size: float

    def build(self, model, builder):
        return Extrusion(Rect(self.size, self.size), self.size).build(model, builder)


@dataclass
class Cylinder(MeshPrimitive):
    """Ngon extruded cylinder primitive"""

    radius: float
    height: float
    segments: int = 8

    def create_mesh(self):
        """Create a polygonal cylinder mesh (ngon extruded)"""
        angle_step = 2 * np.pi / self.segments
        bottom = [
            (float(self.radius * np.cos(i * angle_step)), float(self.radius * np.sin(i * angle_step)), 0)
            for i in range(self.segments)
        ]
        top = [(float(x), float(y), self.height) for (x, y, _) in bottom]
        vertices = bottom + top
        faces = []
        for i in range(self.segments):
            next_i = (i + 1) % self.segments
            faces.append((i, next_i, i + self.segments))
            faces.append((next_i, next_i + self.segments, i + self.segments))
        bottom_face = tuple(range(self.segments - 1, -1, -1))
        faces.append(bottom_face)
        return vertices, faces

    def as_representation(self, color: str = "128, 128, 128"):
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices, faces, color)


@dataclass
class Sphere(MeshPrimitive):
    """Icosphere primitive"""

    radius: float
    detail: int = 1

    def create_mesh(self):
        """Create an icosphere mesh"""
        vertices, faces = icosphere_lib(self.detail)
        vertices = [tuple(map(float, v)) for v in vertices]
        faces = [list(map(int, f)) for f in faces]
        # Scale vertices to the given radius
        vertices = [(x * self.radius, y * self.radius, z * self.radius) for (x, y, z) in vertices]
        return vertices, faces

    def as_representation(self, color: str = "128, 128, 128"):
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices, faces, color)


@dataclass
class NullpunktWithArrowObject(MeshPrimitive):
    """Geometric base point object with a north arrow and 'N' on the top face using parametric coordinates."""
    size: float
    arrow_color: str = "50, 50, 50"  # Dark gray

    def _get_n_coordinates(self):
        """Get N letter coordinates with scale factor, extruded 20mm above surface"""
        base_coords = [
            (-0.05, 0.35), (-0.033, 0.35), (-0.033, 0.425), (0.033, 0.35),
            (0.05, 0.35), (0.05, 0.45), (0.033, 0.45), (0.033, 0.375),
            (-0.033, 0.45), (-0.05, 0.45), (-0.05, 0.35)
        ]
        
        # Scale coordinates and add Z coordinate (extruded 20mm above surface)
        z_base = 1.0 * self.size  # Base surface
        z_extruded = (1.0 + 0.02) * self.size  # 20mm above surface
        
        vertices = []
        # Add base vertices
        for x, y in base_coords:
            vertices.append((x * self.size, y * self.size, z_base))
        # Add extruded vertices
        for x, y in base_coords:
            vertices.append((x * self.size, y * self.size, z_extruded))
        
        return vertices

    def create_mesh(self):
        """Create complete basepoint mesh with solid top face"""
        # Full basepoint coordinates
        vertices = [
            # Base vertices (same as NullpunktObject)
            (-0.5 * self.size, -0.5 * self.size, 1.0 * self.size),  # 0: top front left
            (0.5 * self.size, -0.5 * self.size, 1.0 * self.size),   # 1: top front right
            (0.5 * self.size, 0.5 * self.size, 1.0 * self.size),    # 2: top back right
            (-0.5 * self.size, 0.5 * self.size, 1.0 * self.size),   # 3: top back left
            (-0.5 * self.size, -0.5 * self.size, -1.0 * self.size), # 4: bottom front left
            (0.5 * self.size, -0.5 * self.size, -1.0 * self.size),  # 5: bottom front right
            (0.5 * self.size, 0.5 * self.size, -1.0 * self.size),   # 6: bottom back right
            (-0.5 * self.size, 0.5 * self.size, -1.0 * self.size),  # 7: bottom back left
            (0.0, 0.0, 0.0),                                        # 8: center point
        ]

        # Define faces for complete basepoint
        faces = [
            # Base star-shaped faces (triangular faces from cube corners to center)
            (0, 1, 8),  # front face triangles
            (1, 2, 8),
            (2, 3, 8),
            (3, 0, 8),
            (5, 4, 8),  # back face triangles
            (6, 5, 8),
            (7, 6, 8),
            (4, 7, 8),
            # Base cube faces (quads)
            (0, 1, 2, 3),  # top face (solid)
            (7, 6, 5, 4),  # bottom face
        ]

        return vertices, faces

    def as_arrow_n_mesh(self):
        """Create separate mesh for arrow and N (extruded 20mm above surface)"""
        vertices = []
        faces = []
        
        # Arrow coordinates (extruded 20mm above surface)
        z_base = 1.0 * self.size  # Base surface
        z_extruded = (1.0 + 0.02) * self.size  # 20mm above surface
        
        arrow_base = [
            (-0.3 * self.size, -0.3 * self.size, z_base),
            (0.3 * self.size, -0.3 * self.size, z_base),
            (0, 0.30015 * self.size, z_base),
        ]
        
        arrow_extruded = [
            (-0.3 * self.size, -0.3 * self.size, z_extruded),
            (0.3 * self.size, -0.3 * self.size, z_extruded),
            (0, 0.30015 * self.size, z_extruded),
        ]
        
        # Add arrow vertices
        arrow_start_idx = len(vertices)
        vertices.extend(arrow_base)
        vertices.extend(arrow_extruded)
        
        # Arrow faces: base triangle, top triangle, and side faces
        faces.append((arrow_start_idx, arrow_start_idx + 1, arrow_start_idx + 2))  # base
        faces.append((arrow_start_idx + 3, arrow_start_idx + 5, arrow_start_idx + 4))  # top
        # Side faces
        faces.append((arrow_start_idx, arrow_start_idx + 3, arrow_start_idx + 4, arrow_start_idx + 1))
        faces.append((arrow_start_idx + 1, arrow_start_idx + 4, arrow_start_idx + 5, arrow_start_idx + 2))
        faces.append((arrow_start_idx + 2, arrow_start_idx + 5, arrow_start_idx + 3, arrow_start_idx))
        
        # N coordinates (extruded)
        n_vertices = self._get_n_coordinates()
        n_start_idx = len(vertices)
        vertices.extend(n_vertices)
        
        # N faces: create extrusion faces
        n_base_count = len(n_vertices) // 2
        n_base_start = n_start_idx
        n_top_start = n_start_idx + n_base_count
        
        # Base face
        base_face = tuple(range(n_base_start, n_base_start + n_base_count))
        faces.append(base_face)
        
        # Top face
        top_face = tuple(range(n_top_start, n_top_start + n_base_count))
        faces.append(top_face)
        
        # Side faces (connecting base to top)
        for i in range(n_base_count):
            next_i = (i + 1) % n_base_count
            faces.append((
                n_base_start + i,
                n_base_start + next_i,
                n_top_start + next_i,
                n_top_start + i
            ))
        
        return MeshRepresentation(vertices, faces, self.arrow_color)

    def create_ifc_mesh_from_mesh(self, mesh, model, body):
        """Create IFC mesh representation from a MeshRepresentation object."""
        return geometry.add_mesh_representation(
            model,
            context=body,
            vertices=[mesh.vertices],
            faces=[mesh.faces]
        )


@dataclass
class MeshRepresentation:
    """Container for mesh geometry data"""

    vertices: List[Tuple[float, float, float]]
    faces: List[List[int]]
    color: str
    transparency: float = 0.0


@dataclass
class Representation:
    items: list

    def build(self, model, builder):
        body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
        return builder.get_representation(context=body, items=[i.build() for i in self.items])


@dataclass
class Product:
    cls: str
    repr: Representation

    def build(self, model, builder):
        element = root.create_entity(model, ifc_class=self.cls)
        geometry.edit_object_placement(model, product=element)
        geometry.assign_representation(model, product=element, representation=self.repr.build())


@dataclass
class Translate:
    item: object
    vec: tuple

    def build(self, model, builder):
        # @todo currently not immutable
        item = self.item.build()
        builder.translate(item, self.vec)
        return item
