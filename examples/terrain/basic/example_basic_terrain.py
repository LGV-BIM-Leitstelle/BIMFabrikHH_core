import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.basic.app import process_terrain_folder_to_ifc
from BIMFabrikHH_core.config.logging_colors import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_tree import BoundingBoxParams, Component, Container, RequestParams

logger = get_logger()


def main():
    """Process terrain files to create a DGM."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = [str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")]
    output_file = terrain_folder / "example_dgm.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_standard",
        components={"description": Component(title="Description", value="Digital Ground Model Component")},
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9756, min_y=53.5522, max_x=9.9789, max_y=53.5536), containers=[container]
    )

    result = process_terrain_folder_to_ifc(terrain_folder, tif_files, 4, 0.9, request_body)

    end = time.perf_counter()
    print(f"Total process time: {end - start:.2f} seconds")

    if result:
        logger.info(
            f"✓ Successfully created {output_file.name}\n{output_file.parent}", extra={"debug_category": "success"}
        )
    else:
        logger.error(f"✗ Failed to create {output_file.name}")


if __name__ == "__main__":
    main()
