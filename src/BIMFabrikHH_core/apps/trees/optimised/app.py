from pathlib import Path

import ifcopenshell.api.root as root
import ifcopenshell.api.spatial as spatial
from ifcfactory import BIMFactoryElement, Transform

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.georeferencing.extract_elevation import extract_elevation_point_from_geotiff
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

from ....core.geometry import Tree, TreeCluster
from ....core.geometry.advanced_objects import create_basepoint_quad

# Configure logger for this module
logger = get_level_logger("trees_optimized_app")


class TreeGenericApp:
    @staticmethod
    def get_elevation(easting, northing, tif_path):
        """
        Get elevation(s) for given easting/northing coordinate(s) from a GeoTIFF file.
        """
        return extract_elevation_point_from_geotiff(easting, northing, tif_path)

    @staticmethod
    def build_ifc_from_tree_data(tree_data, output_path=None, use_geotiff_elevation=False, tif_path=None):
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(
            project_name="MyProject",
            coordinate_system=CoordinateSystemTemplates.epsg_25832(),
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name="MySite",
            building_name="MyBuilding",
        )
        model = builder.model
        body = builder.body
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")
        ifc_snippets = IfcSnippets()

        # Optionally update tree elevations from GeoTIFF
        if use_geotiff_elevation and tif_path is not None:
            for row in tree_data:
                easting = row.get("Easting")
                northing = row.get("Northing")
                if easting is not None and northing is not None:
                    elevation = TreeGenericApp.get_elevation(easting, northing, tif_path)
                    # Only update if elevation is found (not 0.0 or None)
                    if elevation is not None and elevation != 0.0:
                        row["Elevation"] = elevation
                    else:
                        logger.warning(
                            f"No elevation found in GeoTIFF for point (E={easting}, N={northing}). Keeping original elevation value."
                        )

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
            TreeGenericApp._create_basepoint_from_bbox(model, storey, tree_data, builder)

        if output_path is None:
            file_path = builder.save_ifc_to_output("output_baum_generic_optimised.ifc")
        else:
            file_path = builder.save_ifc_to_output(str(Path(output_path).name))
        logger.info(f"IFC model saved to {file_path}")
        return file_path

    @staticmethod
    def _create_basepoint_from_bbox(model, storey, tree_data, builder):
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

        # Create and add basepoint with arrow using new BIMFactoryElement pattern
        basepoint_entity = BIMFactoryElement(
            inst=builder.site or storey,
            children=[
                Transform(
                    vec=basepoint_position,
                    item=create_basepoint_quad(size=8.0, psets=basepoint_data["psets"]),
                ),
            ],
        ).build(model)

        logger.info(f"Created basepoint at lower-left corner: ({min_x:.2f}, {min_y:.2f})")

    @staticmethod
    def build_ifc_with_trees_and_basepoints(tree_data, basepoint_data, output_path=None):
        """Build IFC model with both trees and basepoints"""
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(
            project_name="MyProject",
            coordinate_system=CoordinateSystemTemplates.epsg_25832(),
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name="MySite",
            building_name="MyBuilding",
        )
        model = builder.model
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

            logger.info(f"Created {len(tree_entities)} trees")

        # Create and add basepoints
        if basepoint_data:
            for i, data in enumerate(basepoint_data, 1):
                logger.info(f"Adding basepoint {i}: size={data.get('size', 5.0)}, position={data['position']}")

                # Create basepoint using new BIMFactoryElement pattern
                basepoint_entity = BIMFactoryElement(
                    inst=builder.site or storey,
                    children=[
                        Transform(
                            vec=data["position"],
                            item=create_basepoint_quad(size=data.get("size", 5.0), psets=data.get("psets", {})),
                        ),
                    ],
                ).build(model)

            logger.info(f"Created {len(basepoint_data)} basepoints")

        if output_path is None:
            file_path = builder.save_ifc_to_output("output_forest_with_basepoints.ifc")
        else:
            file_path = builder.save_ifc_to_output(str(Path(output_path).name))
        logger.info(f"IFC model saved to {file_path}")
        return file_path
