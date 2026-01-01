"""Example showing how to use the modular city app with input data."""

import logging
import time
from pathlib import Path

from BIMFabrikHH_core.apps.city.app import CityModularApp
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Run the modular city example."""
    print("=== Modular City Example ===")

    # Start timing
    start_time = time.time()

    # Sample building data (from GML files)
    gml_files = ["LoD2_32_564_5934_1_HH.xml", "LoD2_32_565_5934_1_HH.xml"]

    # Use relative path that works both when run directly and from all_examples.py
    folder_path = Path(__file__).parent.parent.parent / "assets"

    # Create city app with GML files
    app = CityModularApp(gml_files, folder_path)

    # Step 1: Get data in bbox
    # bbox = BoundingBoxParams(min_x=9.9714, min_y=53.5522, max_x=9.9875, max_y=53.5586)
    bbox = BoundingBoxParams(min_x=9.9739, min_y=53.5542, max_x=9.9803, max_y=53.5572)

    raw_buildings = app.get_data_in_bbox(bbox)
    print(f"Got {len(raw_buildings)} raw buildings")

    # Step 2: Process data
    processed_buildings = app.process_data(raw_buildings)
    print(f"Processed {len(processed_buildings)} buildings")

    # Step 3: Create IFC
    container = Container(
        containerTitle="City Model",
        containerId="city_model",
        components={
            "project": Component(title="Project Name", value="Hamburg City Model"),
            "site": Component(title="Site Name", value="Hamburg"),
            "building": Component(title="Building Name", value="City Buildings"),
        },
    )

    request_params = RequestParams(bbox=bbox, containers=[container])
    ifc_path = app.create_ifc(processed_buildings, request_params)
    print(f"IFC saved to: {ifc_path}")

    # Calculate and display total time
    total_time = time.time() - start_time
    print(f"=== Example completed in {total_time:.2f} seconds ===")
    return ifc_path


if __name__ == "__main__":
    main()
