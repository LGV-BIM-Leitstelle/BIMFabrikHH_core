from pathlib import Path

import ifcopenshell.api.root as root

from .tree_model import Tree, TreeCluster
from ....core.georeferencing.extract_elevation import extract_elevation_df_from_geotiff
from ....core.ifc_modelbuilder import IfcModelBuilder
from ....core.ifc_snippets import IfcSnippets


class BaumGenericElevationApp:
    @staticmethod
    def get_elevation(easting, northing, tif_path):
        """
        Get elevation(s) for given easting/northing coordinate(s) from a GeoTIFF file.
        Args:
            easting (float or list of float): Easting (X) coordinate(s).
            northing (float or list of float): Northing (Y) coordinate(s).
            tif_path (str): Path to the GeoTIFF file.
        Returns:
            float or list of float: Elevation(s) at the given coordinate(s).
        """
        return extract_elevation_df_from_geotiff(easting, northing, tif_path)

    @staticmethod
    def build_ifc_from_tree_data(tree_data, output_path=None):
        """
        Build an IFC model from a list of tree data dicts and save to file.
        Args:
            tree_data (list of dict): List of tree data dicts (each with position, etc.)
            output_path (str or Path, optional): Path to save the IFC file.
            If None, saves to output_baum_generic.ifc in current dir.
        Returns:
            Path: Path to the saved IFC file.
        """
        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(project_name="MyProject", site_name="MySite", building_name="MyBuilding")
        model = builder.get_model()
        body = builder.body
        ifc_snippets = IfcSnippets()
        storey = root.create_entity(model, ifc_class="IfcBuildingStorey", name="Default Storey")

        forest = TreeCluster([Tree.from_standardized_data(row) for row in tree_data])
        for idx, tree in enumerate(forest.trees, 1):
            tree.build(None, model, body, storey, idx, ifc_snippets)

        if output_path is None:
            output_path = Path(__file__).parent / "output_baum_generic.ifc"
        else:
            output_path = Path(output_path)
        model.write(str(output_path))
        print(f"IFC model saved to {output_path}")
        return output_path
