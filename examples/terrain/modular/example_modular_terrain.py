"""Example showing how to use the modular terrain app with input data."""

import logging

from BIMFabrikHH_core.apps.terrain.filtered.app import TerrainModularApp
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run the modular terrain example."""
    print("=== Modular Terrain Example ===")

    # Sample terrain data (GeoTIFF files)
    tif_name = str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")
    tif_files = [tif_name]

    # Create terrain app with GeoTIFF files
    app = TerrainModularApp(tif_files)

    # Step 1: Get data in bbox
    bbox = BoundingBoxParams(min_x=9.877815, min_y=53.492363, max_x=9.887343, max_y=53.496003)
    raw_terrain = app.get_data_in_bbox(bbox)
    print(f"Got {len(raw_terrain)} terrain tiles")

    # Step 2: Process data
    processed_terrain = app.process_data(raw_terrain)
    print("Processed terrain data")

    # Step 3: Create IFC
    container = Container(
        containerTitle="DGM_Container",
        containerId="filtered",
        components={
            "description": Component(title="Description", value="Filtered Digital Ground Model Component"),
        },
    )

    request_params = RequestParams(bbox=bbox, containers=[container])
    ifc_path = app.create_ifc(processed_terrain, request_params)
    print(f"IFC saved to: {ifc_path}")

    print("=== Example completed ===")
    return ifc_path


if __name__ == "__main__":
    main()
