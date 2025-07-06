"""
Primitive Geometry Objects
=========================

This module contains the core primitive objects for composable geometry creation.
These dataclasses can be used to build complex geometry arrangements in a
declarative, composable way.
"""

# postponed annotations for Element.children : list[Element]
from __future__ import annotations

from typing import List, Tuple, Optional, Type, Union
from enum import Enum
from abc import ABC

import ifcopenshell
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.feature
import ifcopenshell.util.representation
import ifcopenshell.util.placement

import numpy as np

from icosphere import icosphere as icosphere_lib
from pydantic import BaseModel, PositiveFloat, model_validator

from ..ifc_snippets import IfcSnippets
from ..ifc_utils import IfcFileCreator


# 'trait' for 2d definitions
class Profile(ABC):
    pass


# 'trait' for representation items
class RepresentationItem(ABC):
    pass


# 'trait' for element (only element and translate)
class ElementInterface(ABC):
    pass


def determine_type(element) -> Union[Type[Profile], Type[RepresentationItem], Type[ElementInterface]]:
    kinds = (Profile, RepresentationItem, ElementInterface)
    is_ = [isinstance(element, kind) for kind in kinds]
    if sum(is_) == 1:
        return kinds[next(k for k, v in enumerate(is_) if v)]
    elif sum(is_) == 0:
        raise TypeError(f"Element of type {type(element).__name__} not supported")
    elif children := getattr(element, "children", None):
        child_types = set(map(determine_type, children))
        if len(child_types) == 1:
            return next(iter(child_types))
        else:
            raise TypeError(f"Inconsistent child types on {type(element).__name__}")
    elif item := getattr(element, "item", None):
        return determine_type(item)
    else:
        raise TypeError(f"Element of type {type(element).__name__} not supported")


class Rect(BaseModel, Profile):
    width: PositiveFloat
    height: PositiveFloat

    def build(self, model, builder):
        return builder.rectangle(size=(self.width, self.height))


class Circle(BaseModel, Profile):
    radius: PositiveFloat

    def build(self, model, builder):
        return model.createIfcCircleProfileDef(
            "AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint((0.0, 0.0))), self.radius
        )


class Extrusion(BaseModel, RepresentationItem):
    basis: Profile
    depth: PositiveFloat

    # For accepting Profile types
    model_config = {"arbitrary_types_allowed": True}

    def build(self, model, builder):
        # @todo can we make this type check in pydantic, is it even necessary?
        basis = self.basis.build(model, builder)
        if basis.is_a("IfcCurve"):
            basis = model.createIfcArbitraryClosedProfileDef("AREA", None, basis)
        elif basis.is_a("IfcProfileDef"):
            pass
        else:
            raise TypeError(f"Instance of type {basis.is_a()} not allowed as extrusion basis")
        return builder.extrude(basis, self.depth)


class Box(BaseModel, RepresentationItem):
    width: PositiveFloat
    depth: PositiveFloat
    height: PositiveFloat

    def build(self, model, builder):
        return Extrusion(basis=Rect(width=self.width, height=self.depth), depth=self.height).build(model, builder)


class Cube(BaseModel, RepresentationItem):
    size: PositiveFloat

    def build(self, model, builder):
        return Box(width=self.size, height=self.size, depth=self.size).build(model, builder)


class NgonCylinder(BaseModel, RepresentationItem):
    """Ngon extruded cylinder primitive"""

    radius: float
    height: float
    segments: int = 8

    def create_mesh(self):
        """Create a polygonal cylinder mesh (ngon extruded)"""
        angle_step = 2 * np.pi / self.segments
        bottom = [
            (float(self.radius * np.cos(i * angle_step)), float(self.radius * np.sin(i * angle_step)), 0) for i in range(self.segments)
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

    def build(self, model, builder):
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices=vertices, faces=faces).build(model, builder)


class Cylinder(BaseModel, RepresentationItem):
    """Ngon extruded cylinder primitive"""

    radius: float
    height: float

    def build(self, model, builder):
        return Extrusion(basis=Circle(radius=self.radius), depth=self.height).build(model, builder)


class Sphere(BaseModel, RepresentationItem):
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

    def build(self):
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices, faces).build()


class NullpunktWithArrowObject(BaseModel, RepresentationItem):
    """Geometric base point object with a north arrow and 'N' on the top face using parametric coordinates."""

    size: float
    arrow_color: str = "50, 50, 50"  # Dark gray

    def _get_n_coordinates(self):
        """Get N letter coordinates with scale factor, extruded 20mm above surface"""
        base_coords = [
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
            (0.5 * self.size, -0.5 * self.size, 1.0 * self.size),  # 1: top front right
            (0.5 * self.size, 0.5 * self.size, 1.0 * self.size),  # 2: top back right
            (-0.5 * self.size, 0.5 * self.size, 1.0 * self.size),  # 3: top back left
            (-0.5 * self.size, -0.5 * self.size, -1.0 * self.size),  # 4: bottom front left
            (0.5 * self.size, -0.5 * self.size, -1.0 * self.size),  # 5: bottom front right
            (0.5 * self.size, 0.5 * self.size, -1.0 * self.size),  # 6: bottom back right
            (-0.5 * self.size, 0.5 * self.size, -1.0 * self.size),  # 7: bottom back left
            (0.0, 0.0, 0.0),  # 8: center point
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
            faces.append((n_base_start + i, n_base_start + next_i, n_top_start + next_i, n_top_start + i))

        return MeshRepresentation(vertices, faces, self.arrow_color)

    def create_ifc_mesh_from_mesh(self, mesh, model, body):
        """Create IFC mesh representation from a MeshRepresentation object."""
        return ifcopenshell.api.geometry.add_mesh_representation(model, context=body, vertices=[mesh.vertices], faces=[mesh.faces])


class MeshRepresentation(BaseModel, RepresentationItem):
    """Container for mesh geometry data"""

    vertices: List[Tuple[float, float, float]]
    faces: List[List[int]]
    # color: str
    # transparency: float = 0.0

    def build(self, model, builder):
        return builder.triangulated_face_set(self.vertices, self.faces)


class Element(BaseModel, ElementInterface):
    type: Optional[str] = None
    inst: Optional[ifcopenshell.entity_instance] = None
    children: List[RepresentationItem | ElementInterface]

    # For accepting children types
    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def check_repr_children(self):
        child_types = set(determine_type(ch) for ch in self.children)
        if len(child_types) > 1:
            raise ValueError(
                f"Elements can contain either other elements or representation items, but not both; Found {' '.join(type(ch).__name__ for ch in self.children)}"
            )
        return self

    @model_validator(mode="after")
    def check_type_inst(self):
        has_type, has_inst = self.type is not None, self.inst is not None
        if has_type == has_inst:
            raise ValueError(f"Either `type` or `inst` needs to be provided")
        return self

    def build(self, model, builder):
        child_type = next(determine_type(ch) for ch in self.children)
        if self.inst:
            element = self.inst
        else:
            element = ifcopenshell.api.root.create_entity(model, ifc_class=self.type)
        ifcopenshell.api.geometry.edit_object_placement(model, product=element)
        if child_type is RepresentationItem:
            body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
            rep = builder.get_representation(context=body, items=[ch.build(model, builder) for ch in self.children])
            ifcopenshell.api.geometry.assign_representation(model, product=element, representation=rep)
        if child_type is ElementInterface:
            ifcopenshell.api.aggregate.assign_object(
                model, products=[ch.build(model, builder) for ch in self.children], relating_object=element
            )
        return element


class Translate(BaseModel, RepresentationItem, Profile, ElementInterface):
    item: object
    vec: tuple

    def build(self, model, builder):
        # @todo currently not immutable/reentrant
        item = self.item.build(model, builder)
        if item.is_a("IfcProduct"):
            m4 = ifcopenshell.util.placement.get_local_placement(item.ObjectPlacement)
            translation = np.eye(4)
            translation[0:3, 3] = self.vec
            ifcopenshell.api.geometry.edit_object_placement(model, item, matrix=translation @ m4)
        else:
            builder.translate(item, self.vec)
        return item


class Style(BaseModel, RepresentationItem):
    item: RepresentationItem
    rgb: Tuple[float, float, float]
    transparency: Optional[float] = None

    # For accepting item
    model_config = {"arbitrary_types_allowed": True}

    def build(self, model, builder):
        inst = self.item.build(model, builder)
        IfcSnippets.assign_color_to_element(model, inst, self.rgb, self.transparency)
        return inst


class BooleanOperationTypes(str, Enum):
    Union = "UNION"
    Intersection = "INTERSECTION"
    Difference = "DIFFERENCE"


class Boolean(BaseModel, RepresentationItem, Profile, ElementInterface):
    operation: BooleanOperationTypes
    children: List[Union[RepresentationItem, Profile, ElementInterface]]

    # For accepting children types
    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def valid_operands(self):
        ty = determine_type(self)
        if ty is None:
            raise ValueError("Invalid type configuration")
        if ty is Profile and self.operation == BooleanOperationTypes.Intersection:
            raise ValueError("Intersections not support on profiles")
        if ty is ElementInterface:
            if self.operation != BooleanOperationTypes.Difference:
                raise ValueError("Only difference supported on elements")
            ch: Element
            for ch in self.children[1:]:
                while isinstance(ch, (Translate, Style)):
                    ch = ch.item
                if ch.type != "IfcOpeningElement":
                    raise ValueError("Only opening elements are supported as second operand element children")
        return self

    def build(self, model, builder):
        ty = determine_type(self)
        chs = [ch.build(model, builder) for ch in self.children]
        if ty == Profile:
            if self.operation == BooleanOperationTypes.Difference:
                # @todo this discards inner curves and ignores other profile types
                chs = [(inst.OuterCurve if inst.is_a("IfcArbitraryClosedProfileDef") else inst) for inst in chs]
                return model.createIfcArbitraryProfileDefWithVoids("AREA", None, chs[0], chs[1:])
            else:
                chs = [(model.createIfcArbitraryClosedProfileDef("AREA", None, inst) if inst.is_a("IfcCurve") else inst) for inst in chs]
                return model.createIfcCompositeProfileDef("AREA", None, chs, None)
        if ty == ElementInterface:
            for op in chs[1:]:
                ifcopenshell.api.feature.add_feature(model, feature=op, element=chs[0])
            return chs[0]
        if ty == RepresentationItem:
            left = chs.pop(0)
            while chs:
                left = model.createIfcBooleanResult(self.operation.value, left, chs.pop(0))
            return left


if __name__ == "__main__":
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
                    Element(
                        type="IfcBuilding",
                        children=[
                            Element(
                                type="IfcWall",
                                children=[
                                    Extrusion(
                                        basis=Boolean(
                                            operation=BooleanOperationTypes.Difference,
                                            children=[
                                                Rect(width=10.0, height=10.0),
                                                Translate(vec=(2.0, 2.0), item=Rect(width=6.0, height=6.0)),
                                            ],
                                        ),
                                        depth=10.0,
                                    )
                                ],
                            )
                        ],
                    )
                ],
            )
        ],
    ).build(model, builder)

    building = model.by_type("IfcBuilding")[0]
    Element(
        inst=building,
        children=[
            Translate(vec=(12.0, 0.0, 0.0), item=Element(type="IfcWall", children=[Style(item=Cube(size=10.0), rgb=(0.8, 0.1, 0.1))]))
        ],
    ).build(model, builder)
    Element(
        inst=building,
        children=[
            Translate(
                vec=(24.0, 0.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        Element(type="IfcWall", children=[Cube(size=10.0)]),
                        Translate(vec=(5.0, 5.0, 5.0), item=Element(type="IfcOpeningElement", children=[Cube(size=5.0)])),
                    ],
                ),
            )
        ],
    ).build(model, builder)
    Element(
        inst=building,
        children=[
            Translate(
                vec=(24.0, 0.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        Element(type="IfcWall", children=[Cube(size=10.0)]),
                        Translate(vec=(5.0, 5.0, 5.0), item=Element(type="IfcOpeningElement", children=[Cube(size=5.0)])),
                    ],
                ),
            )
        ],
    ).build(model, builder)
    Element(
        inst=building,
        children=[Element(type="IfcWall", children=[Translate(vec=(41.0, 5.0, 0.0), item=NgonCylinder(radius=5.0, height=10.0))])],
    ).build(model, builder)
    Element(
        inst=building,
        children=[Element(type="IfcWall", children=[Translate(vec=(53.0, 5.0, 0.0), item=Cylinder(radius=5.0, height=10.0))])],
    ).build(model, builder)

    model.write("test.ifc")
