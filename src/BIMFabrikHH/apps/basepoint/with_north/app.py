from pathlib import Path

import ifcopenshell.api.root as root
import ifcopenshell.api.spatial as spatial

from ....core.geometry.basepoint_objects import BasePointNorth
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_snippets import IfcSnippets


class BasepointNorthApp:
    @staticmethod
    def build_ifc_from_basepoint_data(basepoint_data, output_path=None):
        """Build IFC model with basepoints that have arrows"""
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(project_name="MyProject", site_name="MySite", building_name="MyBuilding")
        model = builder.get_model()
        body = builder.body
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
        ifc_snippets = IfcSnippets()

        # Create and add basepoints with arrows
        basepoint_entities = []
        for i, data in enumerate(basepoint_data, 1):
            print(f"Adding basepoint with arrow {i}: size={data.get('size', 5.0)}, position={data['position']}")

            # Create BasePointNorth object
            basepoint = BasePointNorth.from_basepoint_data(data)

            # Create IFC product
            basepoint_entity = basepoint.as_product(model, builder)

            # Assign to site (or storey as fallback)
            if builder.site:
                spatial.assign_container(model, relating_structure=builder.site, products=[basepoint_entity])
            else:
                spatial.assign_container(model, relating_structure=storey, products=[basepoint_entity])

            basepoint_entities.append(basepoint_entity)

        print(f"Created {len(basepoint_entities)} basepoints with north")

        if output_path is None:
            output_path = Path(__file__).parent / "output_basepoint_with_north.ifc"
        else:
            output_path = Path(output_path)
        model.write(str(output_path))
        print(f"IFC model saved to {output_path}")
        return output_path

    @staticmethod
    def build_basepoint_north(position=(0, 0, 0), size=5.0, output_path=None, psets=None):
        """Build IFC model with a single basepoint with north"""

        basepoint_data = [
            {
                "position": position,
                "size": size,
                "psets": psets,
            }
        ]

        return BasepointNorthApp.build_ifc_from_basepoint_data(basepoint_data, output_path)
