"""
Sachsen terrain example using the filtered terrain app.

Uses the DGM GeoTIFF from examples/assets/data_sachsen/dgm1_33410_5652_2_sn_tiff
and creates an IFC terrain model via BIMFabrikHH_core.apps.terrain.filtered.

Runs without bbox so the full raster is used (any CRS, e.g. EPSG:25833).
"""
import time
from pathlib import Path

from BIMFabrikHH_core import Component, Container, RequestParams
from BIMFabrikHH_core.apps.terrain.filtered import process_terrain_folder_to_ifc
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()

# Sachsen DGM tile: folder and single GeoTIFF
SACHSEN_TIFF_FOLDER = PathConfig.ASSETS / "data_sachsen" / "dgm1_33410_5652_2_sn_tiff"
SACHSEN_TIFF_FILES = ["dgm1_33410_5652_2_sn.tif"]


def main():
    """Process Sachsen terrain GeoTIFF to create a filtered DGM IFC."""
    start = time.perf_counter()

    output_dir = PathConfig.OUTPUT
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "output_dgm_sachsen.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="filtered",
        components={
            "description": Component(
                title="Description",
                value="Filtered DGM from Sachsen (dgm1_33410_5652_2_sn)",
            )
        },
    )

    # No bbox: use full raster (avoids CRS mismatch for Sachsen / EPSG:25833).
    request_body = RequestParams(bbox=None, containers=[container])

    result = process_terrain_folder_to_ifc(
        folder_path=SACHSEN_TIFF_FOLDER,
        tif_files=SACHSEN_TIFF_FILES,
        min_points=500,
        importance_threshold=0.05,
        input_data=request_body,
        move_to_origin=False,
        output_path=output_path,
    )

    end = time.perf_counter()
    print(f"Total process time: {end - start:.2f} seconds")
    print(f"IFC model saved to: {output_path}")

    if result:
        logger.info(
            f"✓ Successfully created {output_path.name}",
            extra={"debug_category": "success"},
        )
    else:
        logger.error(f"✗ Failed to create {output_path.name}", extra={"debug_category": "error"})


if __name__ == "__main__":
    main()
