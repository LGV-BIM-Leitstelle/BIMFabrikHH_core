"""
Advanced Geometry Objects
=========================

This module contains advanced geometry objects that build upon the
primitive objects. These dataclasses represent complex geometric
components with sophisticated mesh generation logic.
"""

from pydantic import BaseModel

from .primitive_objects import Element, ElementInterface, MeshRepresentation, ExtrudedNgonAsMesh, Style


class ProjectBasePointMesh(MeshRepresentation):
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

    def model_post_init(self, _):
        self.vertices, self.faces = self.create_mesh()


class ProjectBasePointNorth(BaseModel, ElementInterface):
    """Geometric base point object with a north arrow and 'N' on the top face, extruded."""
    size: float

    def _get_n_coordinates(self):
        """Get N letter coordinates with scale factor, to be extruded 20mm above surface"""
        xys = [
            (-0.05, 0.35), (-0.033, 0.35), (-0.033, 0.425), (0.033, 0.35),
            (0.05, 0.35), (0.05, 0.45), (0.033, 0.45), (0.033, 0.375),
            (-0.033, 0.45), (-0.05, 0.45), (-0.05, 0.35)
        ]
        z_base = 1.0 * self.size  # Base surface
        return [xy + (z_base,) for xy in xys]

    def _get_arrow_coordinates(self):
        """Create separate mesh for arrow and N to be extruded 20mm above surface"""
        xys = [
            (-0.3 * self.size, -0.3 * self.size),
            (0.3 * self.size, -0.3 * self.size),
            (0, 0.30015 * self.size),
        ]
        z_base = 1.0 * self.size  # Base surface
        return [xy + (z_base,) for xy in xys]
    
    def build(self, model, builder):
        return Element(type="IfcBuildingElementProxy", children=[
            Style(rgb=(0.7, 0.7, 0.7), item=ProjectBasePointMesh(size=self.size)),
            Style(rgb=(0.1, 0.1, 0.1), item=ExtrudedNgonAsMesh(basis=self._get_n_coordinates(), height=0.02)),
            Style(rgb=(0.4, 0.4, 0.4), item=ExtrudedNgonAsMesh(basis=self._get_arrow_coordinates(), height=0.02))
        ]).build(model, builder)
    
if __name__ == "__main__":
    import ifcopenshell.util.shape_builder
    from ..ifc_utils import IfcFileCreator

    model = IfcFileCreator.create_model("IFC4")
    proj = IfcFileCreator.create_project(model, "my_project")[0]
    IfcFileCreator.create_units_meter(model)
    IfcFileCreator.create_contexts(model)

    builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

    Element(
        inst=proj,
        children=[
            Element(
                type="IfcSite",
                children=[
                    ProjectBasePointNorth(size=1.)
                ],
            )
        ],
    ).build(model, builder)

    model.write("basepoint.ifc")