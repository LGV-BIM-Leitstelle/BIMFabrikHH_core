import time
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.terrain.filtered import process_terrain_folder_to_ifc
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()


def main():
    """Process terrain files to create a filtered DGM."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_name = str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")
    # tif_path = terrain_folder / tif_name

    tif_files = [tif_name]

    output_file = terrain_folder / "example_dgm_filtered.ifc"
    ifc_output_path = PathConfig.OUTPUT / "output_dgm_optimized.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="filtered",
        components={"description": Component(title="Description", value="Filtered Digital Ground Model Component")},
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.8803, min_y=53.4931, max_x=9.887343, max_y=53.496003), containers=[container]
    )

    # Move mesh to origin
    result = process_terrain_folder_to_ifc(terrain_folder, tif_files, 500, 0.05, request_body, move_to_origin=True)

    end = time.perf_counter()
    print(f"Total process time: {end - start:.2f} seconds")
    print(f"IFC model saved to: {ifc_output_path}")

    if result:
        logger.info(
            f"✓ Successfully created {output_file.name}\n{output_file.parent}", extra={"debug_category": "success"}
        )
    else:
        logger.error(f"✗ Failed to create {output_file.name}", extra={"debug_category": "error"})


if __name__ == "__main__":
    main()
