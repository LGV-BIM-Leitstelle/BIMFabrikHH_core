from dataclasses import dataclass

import ifcopenshell
import ifcopenshell.api.material.add_material
import ifcopenshell.util.placement
import ifcopenshell.util.representation


# 'trait' for 2d definitions
class profile:
    pass


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
        element = ifcopenshell.api.root.create_entity(model, ifc_class=self.cls)
        ifcopenshell.api.geometry.edit_object_placement(model, product=element)
        ifcopenshell.api.geometry.assign_representation(model, product=element, representation=self.repr.build())


@dataclass
class Translate:
    item: object
    vec: tuple

    def build(self, model, builder):
        # @todo currently not immutable
        item = self.item.build()
        builder.translate(item, self.vec)
        return item
