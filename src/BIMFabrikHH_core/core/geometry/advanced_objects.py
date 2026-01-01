"""
Advanced Geometry Objects
=========================

This module contains advanced geometry objects that build upon the
primitive objects. These dataclasses represent complex geometric
components with sophisticated mesh generation logic.
"""

from typing import Annotated, Any, ClassVar, List, Optional

import ifcopenshell
from ifcfactory import BIMFactoryElement, ElementInterface, Extrusion, MeshRepresentation, Polygon, Style, Transform
from pydantic import BaseModel, Field

from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Georeferenzierung,
    Pset_Hyperlink,
    Pset_Modellinformation,
    Pset_Objektinformation,
)


def convert_psets_from_dict(psets_dict):
    """
    Convert dictionary of property sets to PropertySetTemplate objects.

    Args:
        psets_dict: Dictionary with pset names as keys and pset data as values

    Returns:
        List of PropertySetTemplate instances
    """
    pset_map = {
        "Pset_Objektinformation": Pset_Objektinformation,
        "Pset_Modellinformation": Pset_Modellinformation,
        "Pset_Georeferenzierung": Pset_Georeferenzierung,
        "Pset_Hyperlink": Pset_Hyperlink,
    }
    return [pset_map[name](**data) for name, data in psets_dict.items() if name in pset_map]


class BaseProjectBasePointNorth(BaseModel):
    """Base class for project base point with north arrow and 'N' on top face."""

    # Geometry constants
    EXTRUSION_HEIGHT: ClassVar[float] = 0.02
    N_SCALE_FACTOR: ClassVar[float] = 0.1
    ARROW_SCALE_FACTOR: ClassVar[float] = 0.3

    # Color constants (RGB tuples with values 0.0-1.0)
    PYRAMID_COLOR: ClassVar[tuple[float, float, float]] = (239 / 255, 109 / 255, 109 / 255)  # coral for pyramid
    ARROW_COLOR: ClassVar[tuple[float, float, float]] = (64 / 255, 64 / 255, 64 / 255)  # Dark gray for N and arrow

    # CAD layer constants
    PYRAMID_LAYER: ClassVar[str] = "_Projektnullpunkt"
    ARROW_LAYER: ClassVar[str] = "_Projektnullpunkt_pfeil"

    size: Annotated[float, Field(gt=0)]

    @classmethod
    def _create_base_pyramid_vertices(cls, size):
        """Create the 9 base vertices for the star pyramid (8 corners + center)"""
        return [
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

    @classmethod
    def _add_void_vertices(cls, vertices, size):
        """
        Add vertices for N and arrow voids to the vertex list.
        Returns the starting indices for each void.
        """
        n_base = cls.get_n_base_coordinates()
        arrow_base = cls.get_arrow_base_coordinates()

        # Add N vertices on top
        n_start_idx = len(vertices)
        vertices.extend([(x * size, y * size, 1.0 * size) for x, y in n_base])

        # Add arrow vertices on top
        arrow_top_start_idx = len(vertices)
        vertices.extend([(x * size, y * size, 1.0 * size) for x, y in arrow_base])

        # Add arrow vertices on bottom
        arrow_bottom_start_idx = len(vertices)
        vertices.extend([(x * size, y * size, -1.0 * size) for x, y in arrow_base])

        return n_start_idx, arrow_top_start_idx, arrow_bottom_start_idx

    @classmethod
    def _create_pyramid_faces(cls, n_start_idx, arrow_top_start_idx, arrow_bottom_start_idx):
        """Create all face definitions including side faces and faces with voids"""
        n_base = cls.get_n_base_coordinates()
        arrow_base = cls.get_arrow_base_coordinates()

        return [
            # Triangular side faces from cube corners to center point (8 faces)
            [0, 8, 1],
            [1, 8, 2],
            [2, 8, 3],
            [3, 8, 0],
            [5, 8, 4],
            [6, 8, 5],
            [7, 8, 6],
            [4, 8, 7],
            # Top face with N and arrow voids (outer CCW, inner boundaries CW)
            [
                [0, 1, 2, 3],  # Outer boundary
                list(reversed(range(n_start_idx, n_start_idx + len(n_base)))),  # N void
                list(reversed(range(arrow_top_start_idx, arrow_top_start_idx + len(arrow_base)))),  # Arrow void
            ],
            # Bottom face with arrow void (outer CCW from below, inner CW from below)
            [
                [4, 5, 6, 7],  # Outer boundary
                list(reversed(range(arrow_bottom_start_idx, arrow_bottom_start_idx + len(arrow_base)))),  # Arrow void
            ],
        ]

    @classmethod
    def create_mesh(cls, size):
        """Create a star-shaped mesh (cube with center point) with N and arrow voids"""
        # Build vertices: base pyramid + void vertices
        vertices = cls._create_base_pyramid_vertices(size)
        n_start_idx, arrow_top_start_idx, arrow_bottom_start_idx = cls._add_void_vertices(vertices, size)

        # Build faces with void definitions
        faces = cls._create_pyramid_faces(n_start_idx, arrow_top_start_idx, arrow_bottom_start_idx)

        return vertices, faces

    @staticmethod
    def get_n_base_coordinates():
        """Get N letter base coordinates (2D, normalized)"""
        return [
            (-0.05, 0.35),
            (-0.033, 0.35),
            (-0.033, 0.425),
            (0.033, 0.35),
            (0.05, 0.35),
            (0.05, 0.45),
            (0.033, 0.45),
            (0.033, 0.375),
            (-0.033, 0.45),
            (-0.05, 0.45),
            (-0.05, 0.35),
        ]

    @staticmethod
    def get_arrow_base_coordinates():
        """Get arrow base coordinates (2D, normalized)"""
        return [
            (-0.3, -0.3),
            (0.3, -0.3),
            (0, 0.30015),
        ]

    def scale_and_position_coordinates(self, base_coords, z_position):
        """
        Scale 2D coordinates and position them at a given Z level.

        Args:
            base_coords: List of (x, y) tuples in normalized coordinates
            z_position: Z position multiplier (e.g., 1.0 for top, -1.0 for bottom)

        Returns:
            List of (x, y, z) tuples scaled by size and positioned at z
        """
        return [(x * self.size, y * self.size, z_position * self.size) for x, y in base_coords]

    def scale_coordinates_2d(self, base_coords):
        """
        Scale 2D coordinates (for polygon extrusion).

        Args:
            base_coords: List of (x, y) tuples in normalized coordinates

        Returns:
            List of (x, y) tuples scaled by size
        """
        return [(x * self.size, y * self.size) for x, y in base_coords]

    def _create_pyramid_mesh(self):
        """Create the star-shaped pyramid mesh using MeshRepresentation (internal)"""
        vertices, faces = self.create_mesh(self.size)
        return MeshRepresentation(vertices=vertices, faces=faces)

    def create_styled_mesh(self, vertices, faces_list):
        """Helper to create a styled mesh representation"""
        return Style(
            rgb=self.ARROW_COLOR,
            item=MeshRepresentation(vertices=vertices, faces=faces_list),
            cad_layer=self.ARROW_LAYER,
        )

    def create_styled_extrusion(self, polygon_points, z_offset, depth):
        """Helper to create a styled extruded shape"""
        return Style(
            rgb=self.ARROW_COLOR,
            item=Transform(
                vec=(0.0, 0.0, z_offset * self.size),
                item=Extrusion(
                    basis=Polygon(points=polygon_points),
                    depth=depth,
                ),
            ),
            cad_layer=self.ARROW_LAYER,
        )

    def get_base_children(self):
        """Get the base pyramid mesh with styling"""
        return [
            Style(
                rgb=self.PYRAMID_COLOR,
                item=self._create_pyramid_mesh(),
                cad_layer=self.PYRAMID_LAYER,
            )
        ]


class ProjectBasePointNorthMesh(BaseProjectBasePointNorth, ElementInterface):
    """Geometric base point object with a north arrow and 'N' on the top face, extruded."""

    type: ClassVar[str] = "IfcBuildingElementProxy"
    psets: Optional[List] = None
    container: Optional[Any] = None

    # For accepting arbitrary types
    model_config = {"arbitrary_types_allowed": True}

    def build(self, model: ifcopenshell.file) -> ifcopenshell.entity_instance:
        # Get scaled coordinates for N and arrow overlay meshes (fill the voids)
        # N letter at top surface (z = 1.0 * size)
        n_coords = self.scale_and_position_coordinates(self.get_n_base_coordinates(), 1.0)
        # Arrow at top surface (z = 1.0 * size)
        arrow_top_coords = self.scale_and_position_coordinates(self.get_arrow_base_coordinates(), 1.0)
        # Arrow at bottom surface (z = -1.0 * size)
        arrow_bottom_coords = self.scale_and_position_coordinates(self.get_arrow_base_coordinates(), -1.0)

        return BIMFactoryElement(
            inst=self.container,
            children=[
                BIMFactoryElement(
                    type="IfcBuildingElementProxy",
                    name=f"Nullpunktobjekt_{self.size}x{self.size}x{self.size}",
                    psets=self.psets or [],
                    children=[
                        *self.get_base_children(),  # Pyramid mesh with voids
                        # Fill voids with dark gray overlay meshes
                        self.create_styled_mesh(n_coords, [tuple(range(len(n_coords)))]),
                        self.create_styled_mesh(arrow_top_coords, [tuple(range(len(arrow_top_coords)))]),
                        self.create_styled_mesh(arrow_bottom_coords, [tuple(range(len(arrow_bottom_coords)))]),
                    ],
                )
            ],
        ).build(model)


def create_basepoint_quad(size: float, psets=None):
    """Create a basepoint quad as a BIMFactoryElement (like the bus station builder pattern)."""
    # Create temporary instance to access methods
    temp_basepoint = BaseProjectBasePointNorth(size=size)

    # Handle psets conversion
    if psets is not None and isinstance(psets, dict):
        psets = convert_psets_from_dict(psets)
    else:
        psets = psets or []

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name="Nullpunktobjekt",
        psets=psets,
        children=[
            *temp_basepoint.get_base_children(),
            # N letter extruded at top surface (2D polygon scaled by size)
            temp_basepoint.create_styled_extrusion(
                temp_basepoint.scale_coordinates_2d(temp_basepoint.get_n_base_coordinates()),
                z_offset=1.0,
                depth=temp_basepoint.EXTRUSION_HEIGHT,
            ),
            # Arrow extruded at top surface (2D polygon scaled by size)
            temp_basepoint.create_styled_extrusion(
                temp_basepoint.scale_coordinates_2d(temp_basepoint.get_arrow_base_coordinates()),
                z_offset=1.0,
                depth=temp_basepoint.EXTRUSION_HEIGHT,
            ),
            # Arrow extruded at bottom surface (2D polygon scaled by size)
            temp_basepoint.create_styled_extrusion(
                temp_basepoint.scale_coordinates_2d(temp_basepoint.get_arrow_base_coordinates()),
                z_offset=-1.0,
                depth=temp_basepoint.EXTRUSION_HEIGHT,
            ),
        ],
    )


class ProjectBasePointNorthQuad(BaseProjectBasePointNorth, ElementInterface):
    """Geometric base point object with a north arrow and 'N' on the top face, using primitive objects."""

    def build(self, model: ifcopenshell.file) -> ifcopenshell.entity_instance:
        """Build the basepoint using primitive objects (kept for compatibility)"""
        return create_basepoint_quad(self.size).build(model)
