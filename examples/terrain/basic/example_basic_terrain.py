"""Basic terrain example.

Creates a DGM from a single GeoTIFF using the adaptive-sampling
:class:`TerrainBasicApp`. The mesh is feature-preserving (Delaunay over
an importance-sampled point cloud with boundary stitching).

Runs without a WGS84 ``bbox`` so the full raster is used. If you want to
crop, pass a ``BoundingBoxParams`` whose WGS84 extent actually overlaps
the raster (the example tile
``dgm1_32_558_9270_1_hh_2022.tif`` covers UTM
``(558000, 5927000) -> (559000, 5928000)`` in EPSG:25832).
"""

import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.basic import TerrainBasicApp
from BIMFabrikHH_core.config.logging_config import get_logger, setup_logging
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

logger = get_logger()


def main() -> None:
    """Process a terrain GeoTIFF to create a basic DGM IFC."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = [str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")]
    output_file = terrain_folder / "example_dgm.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_basic",
        components={"description": Component(title="Description", value="Digital Ground Model (basic)")},
    )
    request_body = RequestParams(bbox=None, containers=[container])

    result = TerrainBasicApp.from_geotiffs(
        tif_files=tif_files,
        request_params=request_body,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_file,
    )

    end = time.perf_counter()
    logger.info(f"Total process time: {end - start:.2f} seconds")

    if result:
        logger.info(
            f"OK Successfully created {output_file.name}\n{output_file.parent}",
            extra={"debug_category": "success"},
        )
    else:
        logger.error(f"X Failed to create {output_file.name}")


if __name__ == "__main__":
    setup_logging()
    main()
