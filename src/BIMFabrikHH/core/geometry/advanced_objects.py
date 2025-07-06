"""
Advanced Geometry Objects
=========================

This module contains advanced geometry objects that build upon the
primitive objects. These dataclasses represent complex geometric
components with sophisticated mesh generation logic.
"""

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from .primitive_objects import MeshRepresentation


# @todo
class MeshPrimitive:
    pass

@dataclass
class ProjectBasePoint(MeshPrimitive):
    """Geometric base point object (project base point) using mesh primitives"""

    size: float

    def create_mesh(self):
        """Create a star-shaped mesh (cube with center point)"""
        size = self.size
        # Define vertices for a cube and a center point
        vertices = [
            (-0.5 * size, -0.5 * size, 1.0 * size),  # 0: top front left
            (0.5 * size, -0.5 * size, 1.0 * size),  # 1: top front right
            (0.5 * size, 0.5 * size, 1.0 * size),  # 2: top back right
            (-0.5 * size, 0.5 * size, 1.0 * size),  # 3: top back left
            (-0.5 * size, -0.5 * size, -1.0 * size),  # 4: bottom front left
            (0.5 * size, -0.5 * size, -1.0 * size),  # 5: bottom front right
            (0.5 * size, 0.5 * size, -1.0 * size),  # 6: bottom back right
            (-0.5 * size, 0.5 * size, -1.0 * size),  # 7: bottom back left
            (0.0, 0.0, 0.0),  # 8: center point
        ]

        # Define faces for the star shape (cube faces + triangular faces to center)
        faces = [
            # Triangular faces from cube corners to center point
            (0, 1, 8),  # front face triangles
            (1, 2, 8),
            (2, 3, 8),
            (3, 0, 8),
            (5, 4, 8),  # back face triangles
            (6, 5, 8),
            (7, 6, 8),
            (4, 7, 8),
            # Cube faces (quads)
            (0, 1, 2, 3),  # top face
            (7, 6, 5, 4),  # bottom face
        ]

        return vertices, faces

    def as_representation(self, color: str = "239, 109, 109"):
        """Create mesh representation"""
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices, faces, color)


@dataclass
class ProjectBasePointNorth(ProjectBasePoint):
    """Geometric base point object with a north arrow and 'N' on the top face, extruded."""

    arrow_color: str = "50, 50, 50"  # Dark gray

    def _get_n_coordinates(self):
        """Get N letter coordinates with scale factor, extruded 20mm above surface"""
        base_coords = [
            (-0.05, 0.35), (-0.033, 0.35), (-0.033, 0.425), (0.033, 0.35),
            (0.05, 0.35), (0.05, 0.45), (0.033, 0.45), (0.033, 0.375),
            (-0.033, 0.45), (-0.05, 0.45), (-0.05, 0.35)
        ]
        z_base = 1.0 * self.size  # Base surface
        z_extruded = (1.0 + 0.02) * self.size  # 20mm above surface
        vertices = []
        for x, y in base_coords:
            vertices.append((x * self.size, y * self.size, z_base))
        for x, y in base_coords:
            vertices.append((x * self.size, y * self.size, z_extruded))
        return vertices

    def as_arrow_n_mesh(self):
        """Create separate mesh for arrow and N (extruded 20mm above surface)"""
        vertices = []
        faces = []
        z_base = 1.0 * self.size
        z_extruded = (1.0 + 0.02) * self.size
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
        arrow_start_idx = len(vertices)
        vertices.extend(arrow_base)
        vertices.extend(arrow_extruded)
        faces.append((arrow_start_idx, arrow_start_idx + 1, arrow_start_idx + 2))
        faces.append((arrow_start_idx + 3, arrow_start_idx + 5, arrow_start_idx + 4))
        faces.append((arrow_start_idx, arrow_start_idx + 3, arrow_start_idx + 4, arrow_start_idx + 1))
        faces.append((arrow_start_idx + 1, arrow_start_idx + 4, arrow_start_idx + 5, arrow_start_idx + 2))
        faces.append((arrow_start_idx + 2, arrow_start_idx + 5, arrow_start_idx + 3, arrow_start_idx))
        n_vertices = self._get_n_coordinates()
        n_start_idx = len(vertices)
        vertices.extend(n_vertices)
        n_base_count = len(n_vertices) // 2
        n_base_start = n_start_idx
        n_top_start = n_start_idx + n_base_count
        base_face = tuple(range(n_base_start, n_base_start + n_base_count))
        faces.append(base_face)
        top_face = tuple(range(n_top_start, n_top_start + n_base_count))
        faces.append(top_face)
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
        from ifcopenshell.api import geometry
        return geometry.add_mesh_representation(
            model,
            context=body,
            vertices=[mesh.vertices],
            faces=[mesh.faces]
        ) 