from pathlib import Path

import ifcopenshell.api.root as root
import ifcopenshell.api.spatial as spatial

from ....core.geometry import BasePointNorth, Tree, TreeCluster
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_snippets import IfcSnippets


class TreeGenericApp:
    @staticmethod
    def build_ifc_from_tree_data(tree_data, output_path=None):
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(project_name="MyProject", site_name="MySite", building_name="MyBuilding")
        model = builder.get_model()
        body = builder.body
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
        ifc_snippets = IfcSnippets()

        # Create Tree objects from data
        trees = [Tree.from_tree_data(row) for row in tree_data]
        forest = TreeCluster(trees)

        # Build the forest using the direct build() method
        tree_entities = forest.build(model, body, storey, ifc_snippets)

        # Assign trees to the site instead of storey
        if builder.site:
            for tree_entity in tree_entities:
                spatial.assign_container(model, relating_structure=builder.site, products=[tree_entity])
        else:
            # Fallback to storey if site is not available
            for tree_entity in tree_entities:
                spatial.assign_container(model, relating_structure=storey, products=[tree_entity])

        # Calculate bounding box and create basepoint
        if tree_data:
            TreeGenericApp._create_basepoint_from_bbox(model, body, storey, tree_data, builder)

        if output_path is None:
            output_path = Path(__file__).parent / "output_baum_generic_optimised.ifc"
        else:
            output_path = Path(output_path)
        model.write(str(output_path))
        print(f"IFC model saved to {output_path}")
        return output_path

    @staticmethod
    def _create_basepoint_from_bbox(model, body, storey, tree_data, builder):
        """Create a basepoint in the lower left corner of the tree bounding box"""
        if not tree_data:
            return

        # Calculate bounding box from tree coordinates
        min_x = min(tree["Easting"] for tree in tree_data)
        min_y = min(tree["Northing"] for tree in tree_data)
        max_x = max(tree["Easting"] for tree in tree_data)
        max_y = max(tree["Northing"] for tree in tree_data)

        # Use the lower-left corner (min_x, min_y) for the basepoint
        basepoint_position = (min_x, min_y, 0)

        # Create basepoint data
        basepoint_data = {
            "position": basepoint_position,
            "size": 8.0,
            "psets": {
                "BasePoint_Properties": {
                    "Name": "Tree Area Reference Point",
                    "Description": f"Reference point for tree area (bbox: "
                    f"{min_x:.2f}, {min_y:.2f} to {max_x:.2f}, {max_y:.2f})",
                    "Type": "Tree_Area_Reference",
                    "Coordinate_System": "UTM32N",
                    "BBox_Min_X": min_x,
                    "BBox_Min_Y": min_y,
                    "BBox_Max_X": max_x,
                    "BBox_Max_Y": max_y,
                }
            },
        }

        # Create and add basepoint with arrow
        basepoint = BasePointNorth.from_basepoint_data(basepoint_data)
        basepoint_entity = basepoint.as_product(model, builder)

        # Assign to site (or storey as fallback)
        if builder.site:
            spatial.assign_container(model, relating_structure=builder.site, products=[basepoint_entity])
        else:
            spatial.assign_container(model, relating_structure=storey, products=[basepoint_entity])

        print(f"Created basepoint at lower-left corner: ({min_x:.2f}, {min_y:.2f})")

    @staticmethod
    def build_ifc_with_trees_and_basepoints(tree_data, basepoint_data, output_path=None):
        """Build IFC model with both trees and basepoints"""
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(project_name="MyProject", site_name="MySite", building_name="MyBuilding")
        model = builder.get_model()
        body = builder.body
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
        ifc_snippets = IfcSnippets()

        # Create and build trees
        if tree_data:
            trees = [Tree.from_tree_data(row) for row in tree_data]
            forest = TreeCluster(trees)
            tree_entities = forest.build(model, body, storey, ifc_snippets)

            # Assign trees to the site instead of storey
            if builder.site:
                for tree_entity in tree_entities:
                    spatial.assign_container(model, relating_structure=builder.site, products=[tree_entity])
            else:
                # Fallback to storey if site is not available
                for tree_entity in tree_entities:
                    spatial.assign_container(model, relating_structure=storey, products=[tree_entity])

            print(f"Created {len(tree_entities)} trees")

        # Create and add basepoints
        if basepoint_data:
            for i, data in enumerate(basepoint_data, 1):
                print(f"Adding basepoint {i}: size={data.get('size', 5.0)}, position={data['position']}")

                # Create BasePointNorth object
                basepoint = BasePointNorth.from_basepoint_data(data)

                # Create IFC product
                basepoint_entity = basepoint.as_product(model, builder)

                # Assign to site (or storey as fallback)
                if builder.site:
                    spatial.assign_container(model, relating_structure=builder.site, products=[basepoint_entity])
                else:
                    spatial.assign_container(model, relating_structure=storey, products=[basepoint_entity])

            print(f"Created {len(basepoint_data)} basepoints")

        if output_path is None:
            output_path = Path(__file__).parent / "output_forest_with_basepoints.ifc"
        else:
            output_path = Path(output_path)
        model.write(str(output_path))
        print(f"IFC model saved to {output_path}")
        return output_path
