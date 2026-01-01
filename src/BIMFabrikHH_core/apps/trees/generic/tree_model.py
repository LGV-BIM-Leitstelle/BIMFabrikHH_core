from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.root as root
import numpy as np
from icosphere import icosphere as icosphere_lib

import BIMFabrikHH_core.data_models.pydantic_psets_tree as psets_module
from BIMFabrikHH_core.core.model_creator import assign_psets_to_element, extract_psets_from_row


def create_trunk_mesh(radius, height, segments=5):
    angle_step = 2 * np.pi / segments
    bottom = [
        (float(radius * np.cos(i * angle_step)), float(radius * np.sin(i * angle_step)), 0) for i in range(segments)
    ]
    top = [(float(x), float(y), height) for (x, y, _) in bottom]
    vertices = bottom + top
    faces = []
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((i, next_i, i + segments))
        faces.append((next_i, next_i + segments, i + segments))
    bottom_face = tuple(range(segments - 1, -1, -1))
    faces.append(bottom_face)
    return vertices, faces


def icosphere(detail):
    vertices, faces = icosphere_lib(detail)
    # Ensure output is in the correct format
    vertices = [tuple(map(float, v)) for v in vertices]
    faces = [list(map(int, f)) for f in faces]
    return vertices, faces


def scale_tree_vertices(vertices, radius):
    return [(x * radius, y * radius, z * radius) for (x, y, z) in vertices]


@dataclass(frozen=True)
class Trunk:
    radius: float
    height: float
    color: str = "111, 70, 46"
    segments: int = 5  # Level of detail for trunk

    def build(self, _builder, model, body, position, idx, ifc_snippets):
        # Create trunk entity
        trunk_entity = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Stamm_{idx:04d}")
        vertices, faces = create_trunk_mesh(self.radius, self.height, self.segments)
        trunk_mesh = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices], faces=[faces], edges=None
        )
        geometry.assign_representation(model, product=trunk_entity, representation=trunk_mesh)
        ifc_snippets.assign_color_to_element(model, trunk_mesh, self.color, 0.0)
        # Place trunk
        trunk_matrix = np.eye(4)
        trunk_matrix[:, 3][0:3] = position
        geometry.edit_object_placement(model, matrix=trunk_matrix, product=trunk_entity)
        return trunk_entity


@dataclass(frozen=True)
class Crown:
    radius: float
    height: float
    color: str = "33, 128, 45"
    detail: int = 1  # Level of detail for crown (icosphere subdivisions)

    def build(self, _builder, model, body, position, idx, ifc_snippets):
        # Create crown entity
        crown_entity = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Krone_{idx:04d}")
        vertices_crown, faces_crown = icosphere(self.detail)
        vertices_crown = scale_tree_vertices(vertices_crown, self.radius)
        crown_mesh = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_crown], faces=[[list(f) for f in faces_crown]], edges=None
        )
        geometry.assign_representation(model, product=crown_entity, representation=crown_mesh)
        ifc_snippets.assign_color_to_element(model, crown_mesh, self.color, 0.0)

        # Place crown (above trunk)
        crown_matrix = np.eye(4)
        crown_matrix[:, 3][0:3] = position
        geometry.edit_object_placement(model, matrix=crown_matrix, product=crown_entity)
        return crown_entity


@dataclass(frozen=True)
class Tree:
    position: Tuple[float, float, float]
    trunk: Trunk
    crown: Crown
    psets: Optional[Dict[str, dict]] = None  # pset name -> properties dict

    @staticmethod
    def compute_trunk_height(crown_radius, height=None):
        if height is not None:
            return height
        kronendurchmesser = crown_radius * 2
        if kronendurchmesser < 3:
            return 3.5
        else:
            return 1.35 * kronendurchmesser

    @classmethod
    def from_standardized_data(cls, row):
        crown_radius = row["kronendurchmesser"] / 2
        circumference_m = row["stammumfang"]
        diameter_m = max(0.05, circumference_m)
        trunk_radius = diameter_m / 2
        trunk_height = cls.compute_trunk_height(crown_radius, row.get("height"))
        detail = row.get("detail", 1)
        position = row["position"]
        psets = extract_psets_from_row(row, psets_module)
        return cls(
            position=position,
            trunk=Trunk(radius=trunk_radius, height=trunk_height, segments=row.get("segments", 8)),
            crown=Crown(radius=crown_radius, height=trunk_height, detail=detail),
            psets=psets,
        )

    def build(self, builder, model, body, _storey, idx, ifc_snippets):
        # Create main tree entity
        tree_entity = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Baum_{idx:04d}")

        # Build trunk at base position
        trunk_entity = self.trunk.build(builder, model, body, self.position, idx, ifc_snippets)

        # Build crown so its center is at the top of the trunk
        crown_pos = (self.position[0], self.position[1], self.position[2] + self.trunk.height)
        crown_entity = self.crown.build(builder, model, body, crown_pos, idx, ifc_snippets)

        # Aggregate trunk and crown under tree_entity
        aggregate.assign_object(model, relating_object=tree_entity, products=[trunk_entity, crown_entity])

        # Add property sets
        if self.psets:
            assign_psets_to_element(model, tree_entity, self.psets, ifc_snippets)
        return tree_entity


@dataclass(frozen=True)
class TreeCluster:
    trees: List[Tree]
