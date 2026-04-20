"""Generic terrain example.

Creates a DGM from a single GeoTIFF using :class:`TerrainGenericApp`
(``ifcfactory`` / ``BIMFactoryElement`` pipeline). The mesh itself is
still produced by the shared adaptive-sampling pipeline — only the IFC
writing strategy differs from the basic app.

Runs without a WGS84 ``bbox`` so the full raster is used.
"""

import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.generic import TerrainGenericApp
from BIMFabrikHH_core.config.logging_colors import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_tree import (
    Component,
    Container,
    RequestParams,
)

logger = get_logger()


def main() -> None:
    """Process a terrain GeoTIFF to create a generic DGM IFC."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = [str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")]
    output_file = terrain_folder / "example_dgm_generic.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_generic",
        components={"description": Component(title="Description", value="Digital Ground Model (generic / ifcfactory)")},
    )
    request_body = RequestParams(bbox=None, containers=[container])

    result = TerrainGenericApp.from_geotiffs(
        tif_files=tif_files,
        request_params=request_body,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_file,
    )

    end = time.perf_counter()
    print(f"Total process time: {end - start:.2f} seconds")

    if result:
        logger.info(
            f"OK Successfully created {output_file.name}\n{output_file.parent}",
            extra={"debug_category": "success"},
        )
    else:
        logger.error(f"X Failed to create {output_file.name}")


if __name__ == "__main__":
    main()
