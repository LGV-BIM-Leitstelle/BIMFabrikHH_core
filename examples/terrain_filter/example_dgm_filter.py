import time
from pathlib import Path

from BIMFabrikHH import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH.apps.terrain.filtered import process_terrain_folder_to_ifc
from BIMFabrikHH.logging_config import get_logger

logger = get_logger()


def main():
    """Process terrain files to create a filtered DGM."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_name = str(Path(__file__).parent.parent / "assets" / "dgm1_32_558_9270_1_hh_2022.tif")
    tif_path = terrain_folder / tif_name
    # If not found, try the examples/terrain folder
    if not tif_path.exists():
        alt_folder = Path(__file__).parent.parent / "terrain"
        tif_path = alt_folder / tif_name
        terrain_folder = alt_folder
    tif_files = [tif_name]

    output_file = terrain_folder / "example_dgm_filtered.ifc"
    ifc_output_path = Path(__file__).parent.parent.parent / "output" / "output_dgm_optimized.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="filtered",
        components={"description": Component(title="Description", value="Filtered Digital Ground Model Component")},
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.877815, min_y=53.492363, max_x=9.887343, max_y=53.496003), containers=[container]
    )

    # Move mesh to origin
    result = process_terrain_folder_to_ifc(terrain_folder, tif_files, 500, 0.05, request_body, move_to_origin=False)

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
