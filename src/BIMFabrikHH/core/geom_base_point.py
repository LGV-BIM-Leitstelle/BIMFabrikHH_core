from typing import Dict, Optional

import numpy as np
from ifcopenshell.api import geometry, root, spatial, pset

from BIMFabrikHH.core.ifc_snippets import IfcSnippets


class BasePoint:
    def __init__(self, model, body, storey):
        self.model = model
        self.body = body
        self.storey = storey
        self.ifc_snippets = IfcSnippets()

    def create_base_point(self, size, x, y, pset_groups):
        vertices = [
            [
                (-0.5 * size, -0.5 * size, 1.0 * size),
                (0.5 * size, -0.5 * size, 1.0 * size),
                (0.5 * size, 0.5 * size, 1.0 * size),
                (-0.5 * size, 0.5 * size, 1.0 * size),
                (-0.5 * size, -0.5 * size, -1.0 * size),
                (0.5 * size, -0.5 * size, -1.0 * size),
                (0.5 * size, 0.5 * size, -1.0 * size),
                (-0.5 * size, 0.5 * size, -1.0 * size),
                (0.0, 0.0, 0.0),
            ]
        ]

        faces = [
            [
                (0, 1, 8),
                (1, 2, 8),
                (2, 3, 8),
                (3, 0, 8),
                (5, 4, 8),
                (6, 5, 8),
                (7, 6, 8),
                (4, 7, 8),
                (0, 1, 2, 3),
                (7, 6, 5, 4),
            ]
        ]

        base_point_object = root.create_entity(
            self.model,
            ifc_class="IfcBuildingElementProxy",
            name=f"_Nullpunktobjekt_{int(size)}x{int(size)}x{int(size)*2}",
        )

        representation = geometry.add_mesh_representation(
            file=self.model, context=self.body, vertices=vertices, faces=faces, edges=None
        )
        geometry.assign_representation(self.model, product=base_point_object, representation=representation)

        # Assign to storey
        spatial.assign_container(self.model, relating_structure=self.storey, products=[base_point_object])

        # Set placement
        base_point_matrix = np.eye(4)
        base_point_matrix[:, 3][0:3] = (float(x) + 5.0, float(y), 0.0)
        geometry.edit_object_placement(self.model, matrix=base_point_matrix, product=base_point_object)

        # Assign color
        self.ifc_snippets.assign_color_to_element(self.model, representation, "239, 109, 109", 0.0)

        # Create property sets
        try:
            for pset_name, pset_data in pset_groups.items():
                self.assign_psets_to_base_point(entity=base_point_object, pset_name=pset_name, pset_data=pset_data)
                # print(f"Pset '{pset_name}' assigned to base point object.")
        except Exception as e:
            print(f"Error creating Psets: {e}")

    def assign_psets_to_base_point(self, entity, pset_name: str, pset_data: Optional[Dict] = None):
        """
        Assigns property sets to the base point object.
        """
        if pset_data is None:
            pset_data = {}

        pset_ifc = pset.add_pset(self.model, product=entity, name=pset_name)

        pset.edit_pset(
            self.model,
            pset=pset_ifc,
            properties=pset_data,
        )
