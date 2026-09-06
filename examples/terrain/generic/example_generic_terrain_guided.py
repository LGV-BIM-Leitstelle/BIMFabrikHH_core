"""Generic terrain example with ALKIS Nutzung Bruchkanten.

DGM1 tiles from ``examples/assets/dgm1_hh_2022-04-30`` for bbox
``9.9769,53.5478–10.0031,53.5564``. Nutzung outlines come from the Hamburg
OAF (``guide_from_oaf=True``). Writing ``alkis_nutzung_weitere.geojson`` is
optional and off by default (``write_geojson=False``).

``trennen=True`` writes one IFC object per Nutzung type (all Flächen of
that type together) plus leftover DGM, each with colour and ALKIS psets.

Pass ``--xml`` to also write a LandXML 1.2 TIN next to the IFC.
"""

import argparse
import sys
import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.generic import TerrainGenericApp
from BIMFabrikHH_core.config.logging_config import get_logger, setup_logging
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_dgm import dgm_tile_paths

logger = get_logger()

# Persist OAF responses as GeoJSON next to the IFC. Off by default.
WRITE_GEOJSON = False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guided DGM example (IFC, optional LandXML).")
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Also write a LandXML 1.2 TIN next to the IFC (off by default).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = dgm_tile_paths()
    output_file = terrain_folder / "example_dgm_generic_guided.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_generic_guided",
        components={
            "description": Component(
                title="Description",
                value="Digital Ground Model with ALKIS Nutzung Bruchkanten",
            )
        },
    )
    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9769, min_y=53.5478, max_x=10.0031, max_y=53.5564),
        containers=[container],
    )

    result = TerrainGenericApp.from_geotiffs(
        tif_files=tif_files,
        request_params=request_body,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_file,
        guide_from_oaf=True,
        write_geojson=WRITE_GEOJSON,
        export_landxml=args.xml,
        trennen=True,
    )

    end = time.perf_counter()
    logger.info("TIMING guided DGM: %.3f s  → %s", end - start, output_file.name)

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
