"""Time unguided vs guided generic DGM on the same tiles and bbox."""

from __future__ import annotations

import sys
import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.generic import TerrainGenericApp
from BIMFabrikHH_core.config.logging_config import get_logger, setup_logging
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

sys.path.insert(0, str(Path(__file__).resolve().parent))
from local_dgm import EXAMPLE_BBOX, dgm_tile_paths, example_guide_records

logger = get_logger()

_HERE = Path(__file__).resolve().parent


def _request(container_id: str, description: str) -> RequestParams:
    return RequestParams(
        bbox=EXAMPLE_BBOX,
        containers=[
            Container(
                containerTitle="DGM_Container",
                containerId=container_id,
                components={"description": Component(title="Description", value=description)},
            )
        ],
    )


def _run(label: str, output_name: str, *, guided: bool) -> tuple[float, Path]:
    tif_files = dgm_tile_paths(EXAMPLE_BBOX)
    output_path = _HERE / output_name
    guide_records = example_guide_records() if guided else None
    t0 = time.perf_counter()
    result = TerrainGenericApp.from_geotiffs(
        tif_files=tif_files,
        request_params=_request(f"dgm_{label}", f"DGM {label}"),
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_path,
        guide_records=guide_records,
    )
    elapsed = time.perf_counter() - t0
    if result is None:
        raise RuntimeError(f"{label} DGM failed")
    return elapsed, result


def main() -> None:
    unguided_s, unguided_path = _run("unguided", "example_dgm_generic.ifc", guided=False)
    guided_s, guided_path = _run("guided", "example_dgm_generic_guided.ifc", guided=True)

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
