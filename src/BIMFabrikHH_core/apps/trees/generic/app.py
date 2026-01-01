from pathlib import Path
from typing import List, Union

import ifcopenshell.api.root as root

from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

from ....core.georeferencing.extract_elevation import extract_elevation_point_from_geotiff
from .tree_model import Tree, TreeCluster


class BaumGenericElevationApp:
    """Application class for building generic tree models with elevation data."""

    @staticmethod
    def get_elevation(
        easting: Union[float, List[float]], northing: Union[float, List[float]], tif_path: str
    ) -> Union[float, List[float]]:
        """
        Get elevation(s) for given easting/northing coordinate(s) from a GeoTIFF file.

        Args:
            easting: Easting (X) coordinate(s).
            northing: Northing (Y) coordinate(s).
            tif_path: Path to the GeoTIFF file.

        Returns:
            Elevation(s) at the given coordinate(s).
        """
        # Convert single values to lists for the function call
        if isinstance(easting, (int, float)):
            easting = [float(easting)]
        if isinstance(northing, (int, float)):
            northing = [float(northing)]

        return extract_elevation_point_from_geotiff(easting, northing, tif_path)

    @staticmethod
    def build_ifc_from_tree_data(tree_data: List[dict], output_path: Union[str, Path, None] = None) -> Path:
        """
        Build an IFC model from a list of tree data dicts and save to file.

        Args:
            tree_data: List of tree data dicts (each with position, etc.)
            output_path: Path to save the IFC file.
                If None, saves to output_baum_generic.ifc in current dir.

        Returns:
            Path to the saved IFC file.
        """
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
        ifc_snippets = IfcSnippets()
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")

        forest = TreeCluster([Tree.from_standardized_data(row) for row in tree_data])
        for idx, tree in enumerate(forest.trees, 1):
            tree.build(None, model, body, storey, idx, ifc_snippets)

        if output_path is None:
            file_path = builder.save_ifc_to_output("output_baum_generic.ifc")
        else:
            file_path = builder.save_ifc_to_output(str(Path(output_path).name))
        print(f"IFC model saved to {file_path}")
        return Path(str(file_path))

    @staticmethod
    def build_ifc_from_tree_data_to_bytes(tree_data: List[dict]) -> bytes:
        """
        Build an IFC model from a list of tree data dicts and return as bytes.

        Args:
            tree_data: List of tree data dicts (each with position, etc.)

        Returns:
            IFC model as bytes for download or in-memory processing.
        """
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
        ifc_snippets = IfcSnippets()
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")

        forest = TreeCluster([Tree.from_standardized_data(row) for row in tree_data])
        for idx, tree in enumerate(forest.trees, 1):
            tree.build(None, model, body, storey, idx, ifc_snippets)

        # Save to bytes instead of file
        ifc_bytes = builder.save_ifc_to_memory()
        if ifc_bytes is None:
            raise RuntimeError("Failed to generate IFC model in memory")
        print(f"IFC model generated in memory: {len(ifc_bytes)} bytes")
        return ifc_bytes
