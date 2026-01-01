import pandas as pd

from BIMFabrikHH_core import BaumModeller, BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.trees import DfColTree
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()


def main():
    """Process tree data to create IFC."""

    container = Container(
        containerTitle="Trees_Container",
        containerId="trees_standard",
        components={
            "description": Component(title="Description", value="Hamburg Trees Component"),
            "type": Component(title="Data Type", value="Tree Inventory"),
        },
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.877815, min_y=53.492363, max_x=9.887343, max_y=53.496003), containers=[container]
    )

    sample_data = [
        {
            DfColTree.EASTING: 558406.01,
            DfColTree.NORTHING: 5927514.51,
            "kronendurchmesser": 18.0,
            "stammumfang": 1.2,
            "baumnummer": "Demo-1",
            "gattung_deutsch": "Ahorn",
            "baumid": 1,
            "art_deutsch": "Spitz-Ahorn",
            "sorte_deutsch": "Spitz-Ahorn",
            "strasse": "Musterweg",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Demo-Bezirk",
            "pflanzjahr": 1990,
        },
        {
            DfColTree.EASTING: 558553.52,
            DfColTree.NORTHING: 5927499.96,
            "kronendurchmesser": 26.0,
            "stammumfang": 2,
            "baumnummer": "Demo-2",
            "gattung_deutsch": "Linde",
            "baumid": 2,
            "art_deutsch": "Winter-Linde",
            "sorte_deutsch": "Winter-Linde",
            "strasse": "Musterweg",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Demo-Bezirk",
            "pflanzjahr": 1985,
        },
    ]

    df = pd.DataFrame(sample_data)

    modeller = BaumModeller()
    tif_path = str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")
    ifc_path = modeller.create_tree_model_from_df(df, request_body, tif_path=tif_path)

    if ifc_path:
        logger.info(f"✓ Successfully created {ifc_path.name}", extra={"debug_category": "success"})
        logger.info(f"Path: {ifc_path.parent}", extra={"debug_category": "success"})

    else:
        logger.error("✗ Failed to create tree IFC model")


if __name__ == "__main__":
    main()
