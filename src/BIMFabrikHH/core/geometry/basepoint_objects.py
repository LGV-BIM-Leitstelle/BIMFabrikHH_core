"""
Basepoint-specific Geometry Objects
==================================

This module contains basepoint-specific geometry objects that build upon the
primitive objects. These dataclasses represent basepoint components with
positioning, property sets, and IFC creation logic.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import ifcopenshell
import ifcopenshell.api.geometry as geometry
import ifcopenshell.api.root as root
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.util.representation
import numpy as np
from BIMFabrikHH.core.ifc_snippets import IfcSnippets

from .primitive_objects import MeshRepresentation
from .advanced_objects import ProjectBasePoint, ProjectBasePointNorth


@dataclass
class BasePoint:
    """Complete basepoint with positioning and property sets"""

    nullpunkt: ProjectBasePoint
    position: Tuple[float, float, float] = (0, 0, 0)
    color: str = "239, 109, 109"  # Red color like original
    psets: Optional[Dict[str, dict]] = None  # pset name -> properties dict

    @classmethod
    def from_basepoint_data(cls, data):
        """Create BasePoint from basepoint data dictionary"""
        # Extract position
        if "position" in data:
            position = data["position"]
        elif "Easting" in data and "Northing" in data:
            position = (data["Easting"], data["Northing"], data.get("Elevation", 0))
        else:
            position = (0, 0, 0)

        # Extract size (configurable from data)
        size = data.get("size", 5.0)  # Default size if not specified

        # Extract color (configurable from data)
        color = data.get("color", "239, 109, 109")

        # Create nullpunkt primitive
        nullpunkt = ProjectBasePoint(size=size)

        # Extract psets if available
        psets = data.get("psets", {})

        return cls(nullpunkt=nullpunkt, position=position, color=color, psets=psets)

    def as_geom(self) -> MeshRepresentation:
        """Create basepoint geometry as mesh representation"""
        return self.nullpunkt.as_representation(color=self.color)

    def as_product(self, model, builder) -> ifcopenshell.entity_instance:
        """Create basepoint as IFC product"""
        # Create IFC mesh representation using primitive
        body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")
        mesh = self.nullpunkt.create_ifc_mesh(model, body)

        # Create basepoint product
        basepoint = root.create_entity(
            model,
            ifc_class="IfcBuildingElementProxy",
            name=f"_Nullpunktobjekt_{int(self.nullpunkt.size)}x{int(self.nullpunkt.size)}x{int(self.nullpunkt.size)*2}",
        )

        # Assign representation and placement
        geometry.edit_object_placement(model, product=basepoint)
        geometry.assign_representation(model, product=basepoint, representation=mesh)

        # Position the basepoint
        matrix = np.eye(4)
        matrix[0, 3] = self.position[0]  # X position
        matrix[1, 3] = self.position[1]  # Y position
        matrix[2, 3] = self.position[2]  # Z position
        geometry.edit_object_placement(model, matrix=matrix, product=basepoint)

        # Add color using IfcSnippets
        IfcSnippets.assign_color_to_element(model, mesh, self.color, 0.0)

        # Add property sets if available
        if self.psets:
            from BIMFabrikHH.core.pset_utils import assign_psets_to_element

            ifc_snippets = IfcSnippets()
            assign_psets_to_element(model, basepoint, self.psets, ifc_snippets)

        return basepoint


@dataclass
class BasePointNorth:
    """Complete basepoint with arrow, positioning and property sets"""

    nullpunkt: ProjectBasePointNorth
    position: Tuple[float, float, float] = (0, 0, 0)
    color: str = "239, 109, 109"  # Red color like original
    arrow_color: str = "50, 50, 50"  # Dark gray for arrow and N
    psets: Optional[Dict[str, dict]] = None  # pset name -> properties dict

    @classmethod
    def from_basepoint_data(cls, data):
        """Create BasePointNorth from basepoint data dictionary"""
        # Extract position
        if "position" in data:
            position = data["position"]
        elif "Easting" in data and "Northing" in data:
            position = (data["Easting"], data["Northing"], data.get("Elevation", 0))
        else:
            position = (0, 0, 0)

        # Extract size (configurable from data)
        size = data.get("size", 5.0)  # Default size if not specified

        # Colors are hardcoded - red for base, dark gray for arrow and N
        color = "239, 109, 109"  # Red color for base
        arrow_color = "50, 50, 50"  # Dark gray for arrow and N

        # Create nullpunkt primitive with arrow
        nullpunkt = ProjectBasePointNorth(size=size, arrow_color=arrow_color)

        # Extract psets if available
        psets = data.get("psets", {})

        return cls(nullpunkt=nullpunkt, position=position, color=color, arrow_color=arrow_color, psets=psets)

    def as_geom(self) -> List[MeshRepresentation]:
        """Create basepoint geometry as list of mesh representations"""
        # Create base mesh representation
        vertices, faces = self.nullpunkt.create_mesh()
        base_geom = MeshRepresentation(vertices, faces, self.color)
        # Get arrow+N mesh representation
        arrow_n_geom = self.nullpunkt.as_arrow_n_mesh()
        return [base_geom, arrow_n_geom]

    def as_product(self, model, builder) -> ifcopenshell.entity_instance:
        """Create basepoint with arrow as IFC product (aggregated assembly)"""
        # Create IFC mesh representation using primitive
        body = ifcopenshell.util.representation.get_context(model, "Model", "Body", "MODEL_VIEW")

        # Create base mesh (red)
        base_mesh = self.nullpunkt.create_ifc_mesh(model, body)
        basepoint = root.create_entity(
            model,
            ifc_class="IfcBuildingElementProxy",
            name=f"_Nullpunktobjekt_{int(self.nullpunkt.size)}x{int(self.nullpunkt.size)}x{int(self.nullpunkt.size)*2}",
        )
        geometry.edit_object_placement(model, product=basepoint)
        geometry.assign_representation(model, product=basepoint, representation=base_mesh)

        # Position the basepoint
        matrix = np.eye(4)
        matrix[0, 3] = self.position[0]  # X position
        matrix[1, 3] = self.position[1]  # Y position
        matrix[2, 3] = self.position[2]  # Z position
        geometry.edit_object_placement(model, matrix=matrix, product=basepoint)

        # Add color using IfcSnippets
        IfcSnippets.assign_color_to_element(model, base_mesh, self.color, 0.0)

        # Create arrow+N mesh (dark gray)
        arrow_n_mesh = self.nullpunkt.as_arrow_n_mesh()
        arrow_n_ifc_mesh = self.nullpunkt.create_ifc_mesh_from_mesh(arrow_n_mesh, model, body)
        arrow_n_product = root.create_entity(
            model, ifc_class="IfcBuildingElementProxy", name="BasePointWithArrow_N_Arrow"
        )
        geometry.edit_object_placement(model, product=arrow_n_product)
        geometry.assign_representation(model, product=arrow_n_product, representation=arrow_n_ifc_mesh)
        geometry.edit_object_placement(model, matrix=matrix, product=arrow_n_product)
        IfcSnippets.assign_color_to_element(model, arrow_n_ifc_mesh, self.arrow_color, 0.0)

        # Create assembly and aggregate both products
        assembly = root.create_entity(model, ifc_class="IfcElementAssembly", name="BasepointWithArrowAssembly")
        aggregate.assign_object(model, products=[basepoint, arrow_n_product], relating_object=assembly)

        # Add property sets if available
        if self.psets:
            from BIMFabrikHH.core.pset_utils import assign_psets_to_element

            ifc_snippets = IfcSnippets()
            assign_psets_to_element(model, assembly, self.psets, ifc_snippets)

        return assembly
