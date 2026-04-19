import logging
from pathlib import Path
from typing import Dict

import pandas as pd

from BIMFabrikHH_core.apps.trees.basic.app import BaumModeller
from BIMFabrikHH_core.apps.trees.basic.baum_manager import BaumManager
from BIMFabrikHH_core.data_models.params_tree import BoundingBoxParams, Component, Container, RequestParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample tree data for demonstration
EXAMPLE_TREES = {
    "trees": [
        {
            "BAUM_NR": "100001",
            "GATTUNG": "Ahorn",
            "KRONENDURCHMESSER": 5.8,
            "STAMMUMFANG": 1.0,
            "Easting": 558553.52,
            "Northing": 5927499.96,
            "Elevation": 17.0,
            "art_deutsch": "Spitz-Ahorn",
            "sorte_deutsch": "Spitz-Ahorn",
            "pflanzjahr": 1990,
        },
        {
            "BAUM_NR": "100002",
            "GATTUNG": "Eiche",
            "KRONENDURCHMESSER": 6.0,
            "STAMMUMFANG": 1.5,
            "Easting": 558553.52,
            "Northing": 5927509.96,
            "Elevation": 17.0,
            "art_deutsch": "Stiel-Eiche",
            "sorte_deutsch": "Stiel-Eiche",
            "pflanzjahr": 1980,
        },
        {
            "BAUM_NR": "100003",
            "GATTUNG": "Linde",
            "KRONENDURCHMESSER": 4.5,
            "STAMMUMFANG": 0.8,
            "Easting": 558553.52,
            "Northing": 5927519.96,
            "Elevation": 17.0,
            "art_deutsch": "Winter-Linde",
            "sorte_deutsch": "Winter-Linde",
            "pflanzjahr": 2000,
        },
        {
            "BAUM_NR": "100004",
            "GATTUNG": "Birke",
            "KRONENDURCHMESSER": 2.0,
            "STAMMUMFANG": 0.45,
            "Easting": 558553.52,
            "Northing": 5927529.96,
            "Elevation": 17.0,
            "art_deutsch": "Hänge-Birke",
            "sorte_deutsch": "Hänge-Birke",
            "pflanzjahr": 1995,
        },
        {
            "BAUM_NR": "100005",
            "GATTUNG": "Buche",
            "KRONENDURCHMESSER": 7.0,
            "STAMMUMFANG": 2.0,
            "Easting": 558553.52,
            "Northing": 5927539.96,
            "Elevation": 17.0,
            "art_deutsch": "Rot-Buche",
            "sorte_deutsch": "Rot-Buche",
            "pflanzjahr": 1975,
        },
    ]
}


class TreeExporter:
    """
    Demonstrates tree export via the basic tree modeller (BaumModeller).
    For Pydantic-based trees, see ``trees/pydantic_example/example_tree_pydantic.py``.
    """

    def __init__(self):
        # Always use the output directory in the same directory as this script
        self.output_dir = Path(__file__).resolve().parent

        self.baum_manager = BaumManager()

    def _prepare_tree_data(self, tree_data: Dict) -> pd.DataFrame:
        """
        Prepare tree data from dictionary input

        Args:
            tree_data (Dict): Dictionary containing tree data with a 'trees' key

        Returns:
            pd.DataFrame: DataFrame containing the tree data
        """
        # Convert list of dictionaries to DataFrame
        df = pd.DataFrame(tree_data["trees"])
        return df

    def export_basic_trees(self, tree_data: Dict, output_file: str = "output_trees_basic.ifc"):
        """
        Export trees using the basic tree modeller
        """
        logger.info("Exporting basic trees...")
        df = self._prepare_tree_data(tree_data)

        # Map column names to match BaumModeller requirements
        df = df.rename(
            columns={
                "KRONENDURCHMESSER": "_Kronendurchmesser",
                "STAMMUMFANG": "_Stammumfang",
                "GATTUNG": "_Gattung",
                "BAUM_NR": "_Baumnummer",
            }
        )

        baum_modeller = BaumModeller()

        # Use WGS84 coordinates for the bounding box
        # Approximate coordinates for the Hamburg area
        bbox_params = BoundingBoxParams(
            min_x=9.9756,
            min_y=53.5522,
            max_x=9.9789,
            max_y=53.5536,  # longitude  # latitude  # longitude  # latitude
        )
        container = Container(
            containerTitle="Trees_Container",
            containerId="trees_standard",
            components={
                "description": Component(title="Description", value="Hamburg Trees Component"),
                "type": Component(title="Data Type", value="Tree Inventory"),
            },
        )
        request_body = RequestParams(bbox=bbox_params, containers=[container])

        # Generate IFC file using BaumModeller
        output_path = self.output_dir / output_file
        result = baum_modeller.create_tree_model_from_df(df, request_body)
        if result:
            logger.info(f"Basic trees exported to {output_path}")
        else:
            logger.error("Basic tree export failed.")


def main():
    """Main function to demonstrate basic tree export."""
    exporter = TreeExporter()
    tree_data = EXAMPLE_TREES
    exporter.export_basic_trees(tree_data)
    logger.info("Tree export completed successfully!")


if __name__ == "__main__":
    main()
