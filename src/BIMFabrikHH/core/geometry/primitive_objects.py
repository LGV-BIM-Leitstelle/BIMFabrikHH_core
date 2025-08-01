"""
Primitive Geometry Objects
=========================

This module contains the core primitive objects for composable geometry creation.
These dataclasses can be used to build complex geometry arrangements in a
declarative, composable way.
"""

# postponed annotations for Element.children : list[Element]
from __future__ import annotations

import functools
import operator
from typing import List, Tuple, Optional, Type, Union
from enum import Enum
from abc import ABC
import typing
import warnings

from ...data_models.pydantic_psets_BIMHH import PropertySetTemplate, Pset_Modellinformation
import ifcopenshell
import ifcopenshell.api.geometry
import ifcopenshell.api.root
import ifcopenshell.api.feature
import ifcopenshell.util.representation
import ifcopenshell.util.placement
import ifc5d.qto

import numpy as np

from icosphere import icosphere as icosphere_lib
from pydantic import BaseModel, PositiveFloat, model_validator, Field

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


class Primitive(BaseModel):
    def children_of_type(self, ty : typing.TypeVar):
        if isinstance(self, ty):
            yield self
        for child in getattr(self, 'children', ()):
            yield from child.children_of_type(ty)
        if child := getattr(self, 'item', ()):
            yield from child.children_of_type(ty)


class Rect(Primitive, Profile):
    width: PositiveFloat
    height: PositiveFloat

    def build(self, model, builder):
        return builder.rectangle(size=(self.width, self.height))


class Circle(Primitive, Profile):
    radius: PositiveFloat

    def build(self, model, builder):
        return model.createIfcCircleProfileDef(
            "AREA", None, model.createIfcAxis2Placement2D(model.createIfcCartesianPoint((0.0, 0.0))), self.radius
        )


class Extrusion(Primitive, RepresentationItem):
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


class Box(Primitive, RepresentationItem):
    width: PositiveFloat
    depth: PositiveFloat
    height: PositiveFloat

    def build(self, model, builder):
        return Extrusion(basis=Rect(width=self.width, height=self.depth), depth=self.height).build(model, builder)


class Cube(Primitive, RepresentationItem):
    size: PositiveFloat

    def build(self, model, builder):
        return Box(width=self.size, height=self.size, depth=self.size).build(model, builder)


class ExtrudedNgonAsMesh(Primitive, RepresentationItem):
    basis: List[Tuple[float, float, float]] = Field(default_factory=list)
    height: float

    def create_mesh(self):
        """Create a polygonal cylinder mesh (ngon extruded)"""
        n_segments = len(self.basis)
        top = (np.array(self.basis) + (0., 0., self.height)).tolist()
        vertices = self.basis + top
        faces = []
        for i in range(n_segments):
            next_i = (i + 1) % n_segments
            faces.append((i, next_i, i + n_segments))
            faces.append((next_i, next_i + n_segments, i + n_segments))
        bottom_face = list(range(n_segments))
        faces.append(bottom_face[::-1])
        top_face = list(range(n_segments, n_segments + n_segments))
        faces.append(top_face)
        return vertices, faces

    def build(self, model, builder):
        vertices, faces = self.create_mesh()
        return MeshRepresentation(vertices=vertices, faces=faces).build(model, builder)


class NgonCylinder(ExtrudedNgonAsMesh):
    """Ngon extruded cylinder primitive"""

    radius: float
    segments: int = 8

    def model_post_init(self, _):
        angle_step = 2 * np.pi / self.segments
        angles = np.arange(self.segments) * angle_step
        x = self.radius * np.cos(angles)
        y = self.radius * np.sin(angles)
        z = np.zeros_like(x)
        self.basis = np.stack((x, y, z), axis=1).tolist()


class Cylinder(Primitive, RepresentationItem):
    """Ngon extruded cylinder primitive"""

    radius: float
    height: float

    def build(self, model, builder):
        return Extrusion(basis=Circle(radius=self.radius), depth=self.height).build(model, builder)


class Sphere(Primitive, RepresentationItem):
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


class MeshRepresentation(Primitive, RepresentationItem):
    """Container for mesh geometry data"""

    # @todo these are default-initialized so that subclasses can be defined that later overwrite these
    # attributes in model_post_init() without having something passed to their __init__() calls. 
    vertices: List[Tuple[float, float, float]] = Field(default_factory=list)
    faces: List[List[int]] = Field(default_factory=list)

    def build(self, model, builder):
        return builder.mesh(self.vertices, self.faces)


class Element(Primitive, ElementInterface):
    guid: str = Field(default_factory=ifcopenshell.guid.new)
    type: Optional[str] = None
    inst: Optional[ifcopenshell.entity_instance] = None
    children: List[RepresentationItem | ElementInterface]
    material: Optional[Material] = None
    psets: List[PropertySetTemplate] = Field(default_factory=list)

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
            element.GlobalId = self.guid
        ifcopenshell.api.geometry.edit_object_placement(model, product=element)
        if child_type is RepresentationItem:
            body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
            rep = builder.get_representation(context=body, items=[ch.build(model, builder) for ch in self.children])
            ifcopenshell.api.geometry.assign_representation(model, product=element, representation=rep)

            # calculate quantities
            ifc5d.qto.edit_qtos(model, ifc5d.qto.quantify(model, [element], ifc5d.qto.rules[f'{model.schema.upper()}QtoBaseQuantities']))
        if child_type is ElementInterface:
            ifcopenshell.api.aggregate.assign_object(
                model, products=[ch.build(model, builder) for ch in self.children], relating_object=element
            )

        if self.material:
            ifcopenshell.api.material.assign_material(model, products=[element], material=self.material.build(model, builder))

        for data in self.psets:
            # @todo this means propertyset data is never shared even if it's the same template instance in python
            pset = ifcopenshell.api.pset.add_pset(model, product=element, name=data.pset_name)
            ifcopenshell.api.pset.edit_pset(model, pset=pset, properties=data.model_dump())

        return element


class Translate(Primitive, RepresentationItem, Profile, ElementInterface):
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


class Style(Primitive, RepresentationItem):
    """
    This is a node in the scene graph to represent a styled representation item
    """
    item: RepresentationItem
    rgb: Tuple[float, float, float]
    transparency: Optional[float] = None

    # For accepting item
    model_config = {"arbitrary_types_allowed": True}

    def build(self, model, builder):
        inst = self.item.build(model, builder)
        IfcSnippets.assign_color_to_element(model, inst, self.rgb, self.transparency)
        return inst

class Material(Primitive):
    name : str
    category : Optional[str] = None
    rgb: Tuple[float, float, float]
    transparency: Optional[float] = None

    def build(self, model, builder):
        if res := getattr(self, '_build_result', None):
            # build it only once
            return res
        inst = ifcopenshell.api.material.add_material(model, name=self.name, category=self.category)
        style = ifcopenshell.api.style.add_style(model)
        ifcopenshell.api.style.add_surface_style(model,
            style=style, ifc_class="IfcSurfaceStyleShading", attributes={
                "SurfaceColour": { "Name": None, "Red": self.rgb[0], "Green": self.rgb[1], "Blue": self.rgb[2]},
                "Transparency": self.transparency,
            })
        context = [x for x in model.by_type('IfcGeometricRepresentationContext') if x.ContextIdentifier == 'Body'][0]
        ifcopenshell.api.style.assign_material_style(model, material=inst, style=style, context=context)
        self._build_result = inst
        return inst

class BooleanOperationTypes(str, Enum):
    Union = "UNION"
    Intersection = "INTERSECTION"
    Difference = "DIFFERENCE"


class Boolean(Primitive, RepresentationItem, Profile, ElementInterface):
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
            element = chs[0]
            for op in chs[1:]:
                ifcopenshell.api.feature.add_feature(model, feature=op, element=element)

            # calculate quantities
            ifc5d.qto.edit_qtos(model, ifc5d.qto.quantify(model, [element], ifc5d.qto.rules[f'{model.schema.upper()}QtoBaseQuantities']))
            return element
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

    concrete = Material(
        name="CON01",
        category="concrete",
        rgb=(0.5,0.5,0.5)
    )
    wood = Material(
        name="WOOD01",
        category="wood",
        rgb=(0.65, 0.50, 0.30),
    )
    glass = Material(
        name="GLASS01",
        category="glass",
        rgb=(0.6, 0.9, 0.8),
        transparency=0.6
    )

    model_info = Pset_Modellinformation(
        # @todo why the underscores?
        _ArtFachmodell="Gebäudemodell",
        _ArtTeilmodell="Tragwerksplanung",
        _Auftraggeber="Freie und Hansestadt Hamburg, Behörde für Stadtentwicklung und Wohnen",
        _Ersteller="Ingenieurbüro Müller GmbH",
        # @todo we should work on different data types so that e.g dates are rendered to a proper semantic type
        _Erstelldatum="2025-07-15",
        _GemObjektkatalog="BIM-Katalog Hamburg 2025",
        _Projektname="Neubau Schulzentrum Altona",
        _Projektnummer="HH-2025-0731"
    )

    Element(
        inst=proj,
        psets=[model_info],
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
                        Element(type="IfcWall", children=[Cube(size=10.0)], material=wood),
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
        children=[Element(type="IfcWall", material=glass, children=[Translate(vec=(41.0, 5.0, 0.0), item=NgonCylinder(radius=5.0, height=10.0))])],
    ).build(model, builder)
    Element(
        inst=building,
        children=[Element(type="IfcWall", material=concrete, children=[Translate(vec=(53.0, 5.0, 0.0), item=Cylinder(radius=5.0, height=10.0))])],
    ).build(model, builder)

    wall_id = ifcopenshell.guid.new()
    wall_elem = Element(
        inst=building,
        children=[Translate(
                vec=(0.0, 15.0, 0.0), 
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        Element(guid=wall_id, type="IfcWall", children=[Box(width=20., depth=0.3, height=3.0)]),
                        Translate(vec=(2.0, -0.5, 1.0), item=Element(type="IfcOpeningElement", children=[Cube(size=1.0)])),
                        # @todo there is no mechanism yet for placing a window/door in an opening
                        Translate(vec=(4.0, -0.5, 1.0), item=Element(type="IfcOpeningElement", children=[Cube(size=1.0)])),
                        Translate(vec=(6.0, -0.5, 1.0), item=Element(type="IfcOpeningElement", children=[Cube(size=1.0)])),
                        Translate(vec=(8.0, -0.5, 1.0), item=Element(type="IfcOpeningElement", children=[Cube(size=1.0)])),
                        Translate(vec=(10.0, -0.5, 1.0), item=Element(type="IfcOpeningElement", children=[Cube(size=1.0)])),
                    ],
                ))
        ],
    )
    wall_elem.build(model, builder)

    qto = ifcopenshell.util.element.get_pset(model[wall_id], 'Qto_WallBaseQuantities')
    wall_box = next(wall_elem.children_of_type(Box))
    almost_eq = lambda a, b: abs(b - a) < 1.e-7
    num_openings = len([el for el in wall_elem.children_of_type(Element) if el.type == 'IfcOpeningElement'])
    gross_vol = functools.reduce(operator.mul, wall_box.model_dump().values())
    assert almost_eq(qto['GrossVolume'], gross_vol)
    assert almost_eq(qto['NetVolume'], gross_vol - (num_openings * 1 * 1 * wall_box.depth))
    assert almost_eq(qto['GrossSideArea'], wall_box.width * wall_box.height)
    assert almost_eq(qto['Height'], wall_box.height)
    assert almost_eq(qto['Length'], wall_box.width)
    assert almost_eq(qto['Width'], wall_box.depth)
    
    model.write("test.ifc")
