"""Generic terrain example (no Bruchkanten).

DGM1 tiles from ``examples/assets/dgm1_hh_2022-04-30`` for bbox
``9.9769,53.5478–9.991435,53.55622`` (Innenstadt / Alster, ~0.90 km²). Same tiles and
crop as the guided example, without constrained street edges.
"""

import sys
import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.generic import TerrainGenericApp
from BIMFabrikHH_core.config.logging_config import get_logger, setup_logging
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_dgm import EXAMPLE_BBOX, dgm_tile_paths

logger = get_logger()


def main() -> None:
    """Process terrain GeoTIFFs to create a generic DGM IFC."""
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = dgm_tile_paths(EXAMPLE_BBOX)
    output_file = terrain_folder / "example_dgm_generic.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_generic",
        components={"description": Component(title="Description", value="Digital Ground Model (generic / ifcfactory)")},
    )
    request_body = RequestParams(
        bbox=EXAMPLE_BBOX,
        containers=[container],
    )

    result = TerrainGenericApp.from_geotiffs(
        tif_files=tif_files,
        request_params=request_body,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_file,
    )

    end = time.perf_counter()
    logger.info("TIMING unguided DGM: %.3f s  → %s", end - start, output_file.name)

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
