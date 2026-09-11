"""Rust terrain example with ALKIS Nutzung Bruchkanten (guided DGM).

Same guided pipeline as ``generic/example_generic_terrain_guided.py`` — DGM1
tiles from ``examples/assets/dgm1_hh_2022-04-30`` for bbox
``9.9769,53.5478–9.991435,53.55622`` (Innenstadt / Alster, ~0.90 km²), Nutzung outlines from
the Hamburg OAF (``guide_from_oaf=True``) — but the IFC is written by Rust via
:class:`TerrainRustApp` (``bimfabrikhh_core_rs.terrain_parts_to_ifc``) instead of
the ifcfactory writer. Python still meshes and splits; Rust only writes STEP.

``merge_parcels=True`` (default) writes Siedlung and Unland as one dark-sand
object. Leftover DGM stays separate. Traffic, Grünfläche, and water stay split.
``split_by_landuse=True`` keeps one object per Nutzung type instead.

Pass ``--xml`` to also write a LandXML 1.2 TIN next to the IFC.
Pass ``--no-merge-parcels`` for one DGM object (Bruchkanten stay in the TIN).
Pass ``--split-by-landuse`` to trennen (one object per Nutzung type).

Needs ``bimfabrikhh_core_rs`` installed (``pip install bimfabrikhh-core-rs``).
"""

import argparse
import sys
import time
from pathlib import Path

from BIMFabrikHH_core.apps.terrain.generic_rust import TerrainRustApp
from BIMFabrikHH_core.config.logging_config import get_logger, setup_logging
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

# Reuse the DGM tile resolver from the generic example (sibling folder).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generic"))
from local_dgm import EXAMPLE_BBOX, dgm_tile_paths

logger = get_logger()

# Persist OAF responses as GeoJSON next to the IFC. Off by default.
WRITE_GEOJSON = False


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guided DGM example written by Rust (IFC, optional LandXML).")
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Also write a LandXML 1.2 TIN next to the IFC (off by default).",
    )
    parser.add_argument(
        "--no-merge-parcels",
        dest="merge_parcels",
        action="store_false",
        help="Do not fold Siedlung/Unland into one Parcels object.",
    )
    parser.add_argument(
        "--split-by-landuse",
        action="store_true",
        help="Trennen: one IFC object per Nutzung type.",
    )
    parser.set_defaults(merge_parcels=True)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    start = time.perf_counter()

    terrain_folder = Path(__file__).parent
    tif_files = dgm_tile_paths(EXAMPLE_BBOX)
    output_file = terrain_folder / "example_dgm_rust_guided.ifc"

    container = Container(
        containerTitle="DGM_Container",
        containerId="dgm_rust_guided",
        components={
            "description": Component(
                title="Description",
                value="Digital Ground Model (Rust writer) with ALKIS Nutzung Bruchkanten",
            )
        },
    )
    request_body = RequestParams(
        bbox=EXAMPLE_BBOX,
        containers=[container],
    )

    result = TerrainRustApp.from_geotiffs(
        tif_files=tif_files,
        request_params=request_body,
        min_points=500,
        importance_threshold=0.05,
        move_to_origin=False,
        output_path=output_file,
        guide_from_oaf=True,
        write_geojson=WRITE_GEOJSON,
        export_landxml=args.xml,
        merge_parcels=args.merge_parcels,
        split_by_landuse=args.split_by_landuse,
    )

    end = time.perf_counter()
    logger.info("TIMING guided DGM (Rust): %.3f s  → %s", end - start, output_file.name)

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
