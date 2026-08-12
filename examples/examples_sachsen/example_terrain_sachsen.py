"""Sachsen terrain example using :class:`TerrainBasicApp`.

Uses the DGM GeoTIFF from ``examples/assets/data_sachsen/dgm1_33410_5652_2_sn_tiff``
and creates an IFC terrain model via the adaptive-sampling basic terrain app.

Runs without a bbox so the full raster is used (any CRS, e.g. EPSG:25833).
"""

import time

from BIMFabrikHH_core import Component, Container, RequestParams
from BIMFabrikHH_core.apps.terrain.basic import TerrainBasicApp
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()

SACHSEN_TIFF_FOLDER = PathConfig.ASSETS / "data_sachsen" / "dgm1_33410_5652_2_sn_tiff"
SACHSEN_TIFF_FILES = ["dgm1_33410_5652_2_sn.tif"]


def main():
    """Process Sachsen terrain GeoTIFF to create a DGM IFC."""
    start = time.perf_counter()

    output_dir = PathConfig.OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "output_dgm_sachsen.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="sachsen",
        components={
            "description": Component(
                title="Description",
                value="DGM from Sachsen (dgm1_33410_5652_2_sn)",
            )
        },
    )

    # No bbox: use full raster (avoids CRS mismatch for Sachsen / EPSG:25833).
    request_body = RequestParams(bbox=None, containers=[container])

    result = TerrainBasicApp.from_geotiffs(
        tif_files=SACHSEN_TIFF_FILES,
        request_params=request_body,
        folder_path=SACHSEN_TIFF_FOLDER,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_path,
    )

    end = time.perf_counter()
    logger.info(f"Total process time: {end - start:.2f} seconds")
    logger.info(f"IFC model saved to: {output_path}")

    if result:
        logger.info(
            f"Successfully created {output_path.name}",
            extra={"debug_category": "success"},
        )
    else:
        logger.error(f"Failed to create {output_path.name}", extra={"debug_category": "error"})


if __name__ == "__main__":
    setup_logging()
    main()
