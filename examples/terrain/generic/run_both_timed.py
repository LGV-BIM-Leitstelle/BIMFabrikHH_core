"""Time unguided vs guided generic DGM on the same tiles and bbox."""

from __future__ import annotations

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

_HERE = Path(__file__).resolve().parent


def _request(container_id: str, description: str) -> RequestParams:
    return RequestParams(
        bbox=BoundingBoxParams(min_x=9.9769, min_y=53.5478, max_x=10.0031, max_y=53.5564),
        containers=[
            Container(
                containerTitle="DGM_Container",
                containerId=container_id,
                components={"description": Component(title="Description", value=description)},
            )
        ],
    )


def _run(label: str, output_name: str, *, guide_from_oaf: bool) -> tuple[float, Path]:
    tif_files = dgm_tile_paths()
    output_path = _HERE / output_name
    t0 = time.perf_counter()
    result = TerrainGenericApp.from_geotiffs(
        tif_files=tif_files,
        request_params=_request(f"dgm_{label}", f"DGM {label}"),
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_path,
        guide_from_oaf=guide_from_oaf,
        write_geojson=False,
    )
    elapsed = time.perf_counter() - t0
    if result is None:
        raise RuntimeError(f"{label} DGM failed")
    return elapsed, result


def main() -> None:
    unguided_s, unguided_path = _run("unguided", "example_dgm_generic.ifc", guide_from_oaf=False)
    guided_s, guided_path = _run("guided", "example_dgm_generic_guided.ifc", guide_from_oaf=True)

    rows = [
        ("unguided (Delaunay)", unguided_s, unguided_path),
        ("guided (CDT Bruchkanten)", guided_s, guided_path),
    ]
    logger.info("")
    logger.info("%-28s  %10s  %10s", "DGM", "seconds", "IFC size")
    logger.info("%s", "-" * 52)
    for label, elapsed, path in rows:
        logger.info("%-28s  %9.3fs  %8.1f KB", label, elapsed, path.stat().st_size / 1024.0)
    logger.info("")
    if unguided_s > 0:
        logger.info("Guided / unguided: %.2fx", guided_s / unguided_s)


if __name__ == "__main__":
    setup_logging()
    main()
