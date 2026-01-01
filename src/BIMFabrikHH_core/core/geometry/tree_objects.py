"""
Tree-specific Geometry Objects
=============================

This module contains tree-specific geometry objects that build upon the
primitive objects. These dataclasses represent tree components like trunks,
crowns, and complete trees.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import ifcopenshell
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.material.add_material
import ifcopenshell.api.root as root
import ifcopenshell.util.placement
import ifcopenshell.util.representation
import numpy as np
from ifcfactory import MeshRepresentation, NgonCylinder, Sphere

import BIMFabrikHH_core.data_models.pydantic_psets_tree as psets_module
from BIMFabrikHH_core.core.model_creator import assign_psets_to_element, extract_psets_from_row
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets


@dataclass
class Trunk:
    """Tree trunk geometry"""

    radius: float
    height: float
    segments: int = 8
    color: str = "139, 69, 19"  # Brown color

    def as_geom(self) -> MeshRepresentation:
        """Create trunk geometry as mesh representation"""
        cylinder = NgonCylinder(radius=self.radius, height=self.height, segments=self.segments)
        return cylinder.as_representation(color=self.color)

    def as_product(self, model, builder) -> ifcopenshell.entity_instance:
        """Create trunk as IFC product"""
        # Create IFC mesh representation using primitive
        body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
        cylinder = NgonCylinder(radius=self.radius, height=self.height, segments=self.segments)
        mesh = cylinder.build(model, builder)

        # Create trunk product
        trunk = root.create_entity(model, ifc_class="IfcBuildingElementProxy")
        geometry.edit_object_placement(model, product=trunk)
        geometry.assign_representation(model, product=trunk, representation=mesh)

        # Add color using IfcSnippets
        IfcSnippets.assign_color_to_element(model, mesh, self.color, 0.0)

        return trunk


@dataclass
class Crown:
    """Tree crown geometry"""

    radius: float
    detail: int = 2
    color: str = "34, 139, 34"  # Green color

    def as_geom(self) -> MeshRepresentation:
        """Create crown geometry as mesh representation"""
        sphere = Sphere(radius=self.radius, detail=self.detail)
        return sphere.as_representation(color=self.color)

    def as_product(self, model, builder) -> ifcopenshell.entity_instance:
        """Create crown as IFC product"""
        # Create IFC mesh representation using primitive
        body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
        sphere = Sphere(radius=self.radius, detail=self.detail)
        mesh = sphere.build(model, builder)

        # Create crown product
        crown = root.create_entity(model, ifc_class="IfcBuildingElementProxy")
        geometry.edit_object_placement(model, product=crown)
        geometry.assign_representation(model, product=crown, representation=mesh)

        # Add color using IfcSnippets
        IfcSnippets.assign_color_to_element(model, mesh, self.color, 0.0)

        return crown


@dataclass
class Tree:
    """Complete tree with trunk and crown"""

    trunk: Trunk
    crown: Crown
    position: Tuple[float, float, float] = (0, 0, 0)
    psets: Optional[Dict[str, dict]] = None  # pset name -> properties dict

    @staticmethod
    def compute_trunk_height(crown_radius, height=None):
        """Compute trunk height based on crown radius or use provided height"""
        if height is not None:
            return height
        kronendurchmesser = crown_radius * 2
        if kronendurchmesser < 3:
            return 3.5
        else:
            return 1.35 * kronendurchmesser

    @classmethod
    def from_tree_data(cls, data):
        """Create Tree from tree data dictionary"""

        # Extract position - data should have "position" as a tuple
        if "position" in data:
            position = data["position"]
        elif "Easting" in data and "Northing" in data:
            position = (data["Easting"], data["Northing"], data.get("Elevation", 0))
        else:
            position = (0, 0, 0)

        # Calculate crown radius from diameter
        crown_radius = data["kronendurchmesser"] / 2

        # Calculate trunk radius from circumference
        circumference_m = data["stammumfang"]
        diameter_m = max(0.05, circumference_m / math.pi)
        trunk_radius = diameter_m / 2

        # Calculate trunk height
        trunk_height = cls.compute_trunk_height(crown_radius, data.get("height"))

        # Get other parameters
        segments = data.get("segments", 8)
        detail = data.get("detail", 1)

        # Extract psets using the existing utility function

        psets = extract_psets_from_row(data, psets_module)

        # Create trunk and crown
        trunk = Trunk(radius=trunk_radius, height=trunk_height, segments=segments)

        crown = Crown(radius=crown_radius, detail=detail)

        return cls(trunk=trunk, crown=crown, position=position, psets=psets)

    def as_geom(self) -> List[MeshRepresentation]:
        """Create tree geometry as list of mesh representations"""
        trunk_geom = self.trunk.as_geom()
        crown_geom = self.crown.as_geom()
        return [trunk_geom, crown_geom]

    def as_product(self, model, builder) -> ifcopenshell.entity_instance:
        """Create tree as IFC product with trunk and crown"""
        # Create trunk and position it at the tree's world position
        trunk_product = self.trunk.as_product(model, builder)
        trunk_matrix = np.eye(4)
        trunk_matrix[0, 3] = self.position[0]  # X position
        trunk_matrix[1, 3] = self.position[1]  # Y position
        trunk_matrix[2, 3] = self.position[2]  # Z position
        geometry.edit_object_placement(model, matrix=trunk_matrix, product=trunk_product)

        # Create crown and position it above the trunk at world coordinates
        crown_product = self.crown.as_product(model, builder)
        crown_pos = (self.position[0], self.position[1], self.position[2] + self.trunk.height)
        crown_matrix = np.eye(4)
        crown_matrix[0, 3] = crown_pos[0]  # X position
        crown_matrix[1, 3] = crown_pos[1]  # Y position
        crown_matrix[2, 3] = crown_pos[2]  # Z position
        geometry.edit_object_placement(model, matrix=crown_matrix, product=crown_product)

        # Create tree aggregate
        tree = root.create_entity(model, ifc_class="IfcBuildingElementProxy")
        tree.Name = "Tree"

        # Aggregate trunk and crown under tree
        ifcopenshell.api.aggregate.assign_object(model, products=[trunk_product], relating_object=tree)
        ifcopenshell.api.aggregate.assign_object(model, products=[crown_product], relating_object=tree)

        # Add property sets if available
        if self.psets:
            ifc_snippets = IfcSnippets()
            assign_psets_to_element(model, tree, self.psets, ifc_snippets)

        return tree


@dataclass
class TreeCluster:
    """Collection of trees"""

    trees: List[Tree]

    def as_geom(self) -> List[MeshRepresentation]:
        """Create cluster geometry as list of mesh representations"""
        geometries = []
        for tree in self.trees:
            geometries.extend(tree.as_geom())
        return geometries

    def as_product(self, model, builder) -> List[ifcopenshell.entity_instance]:
        """Create cluster as list of IFC products"""
        return [tree.as_product(model, builder) for tree in self.trees]

    def build(self, model, body, storey, ifc_snippets):
        """Build all trees in the cluster (legacy interface)"""
        entities = []
        for idx, tree in enumerate(self.trees, 1):
            # Create a proper builder object that has the required methods
            class ProperBuilder:
                def __init__(self, model, body):
                    self.model = model
                    self.body = body

                def triangulated_face_set(self, vertices, faces):
                    """Create a triangulated face set representation"""
                    import ifcopenshell.api.geometry as geometry

                    return geometry.add_mesh_representation(
                        self.model, context=self.body, vertices=[vertices], faces=[faces], edges=[[]]
                    )

            builder = ProperBuilder(model, body)
            tree_entity = tree.as_product(model, builder)
            entities.append(tree_entity)
        return entities
