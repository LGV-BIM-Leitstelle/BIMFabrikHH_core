"""
Sachsen generic-entity example — one building, a batch, or full tile, LoD2.

Each surface (wall, roof, ground, …) becomes its own typed IFC product
(``IfcWall``, ``IfcRoof``, ``IfcSlab``, …) inside one ``IfcBuilding`` per
CityGML building.

Usage
-----
- Set ``BUILDING_ID`` to a ``gml:id`` string to export a single building.
- Set ``BUILDING_ID = None`` + ``BATCH_SIZE = None`` to export the full tile
  as one file (only practical for small tiles).
- Set ``BATCH_SIZE`` to split the tile into multiple files of N buildings each,
  which keeps memory under control for large tiles.

Each boundary surface element receives a ``BIMFabrikHH_Quantities`` property
set with ``GrossArea``, ``Perimeter``, ``Tilt``, and ``SurfaceType``,
computed directly from the polygon ring coordinates.
"""

from __future__ import annotations

import gc
import time
from typing import List, Optional

from BIMFabrikHH_core.apps.city import CityGenericEntityApp
from BIMFabrikHH_core.apps.city.generic_entity import parse_typed_gml_files
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import TypedCityBuilding

logger = get_logger()

# Set to a gml:id string to export one building, or None for all.
BUILDING_ID: Optional[str] = None  # "DESNATPU1000C1qE"

# Number of buildings per output file. None = one file for everything.
BATCH_SIZE: Optional[int] = 250

# Hard cap on total buildings processed. None = no limit.
MAX_BUILDINGS: Optional[int] = None

SACHSEN_DATA = PathConfig.ASSETS / "data_sachsen"
GML_FILE = SACHSEN_DATA / "lod2_33410_5652_2_sn_citygml" / "lod2_33410_5652_2_sn.gml"

LOG_BOUNDARY_KINDS = False


def _build_batch(
    batch: List[TypedCityBuilding],
    batch_index: int,
    request_params: RequestParams,
) -> None:
    label = f"batch_{batch_index:03d}"
    output_path = PathConfig.OUTPUT / f"output_generic_entity_sachsen_{label}.ifc"

    logger.info("Building IFC %s (%d buildings)…", label, len(batch))
    t = time.perf_counter()
    result = CityGenericEntityApp.build_ifc(
        batch,
        request_params=request_params,
        output_path=output_path,
        coordinate_system=CoordinateSystemTemplates.epsg_25833(),
        color=(1.0, 0.8, 0.4),
        export_quantity_sets=False,
    )
    elapsed = time.perf_counter() - t

    if result:
        logger.info("OK  %s  (%.2fs)", result, elapsed, extra={"debug_category": "success"})
    else:
        logger.error("FAIL  %s  (%.2fs)", label, elapsed, extra={"debug_category": "error"})


def main() -> None:
    request_params = RequestParams(
        bbox=None,
        containers=[
            Container(
                containerTitle="Projektinformationen",
                containerId="Projektinformationen",
                components={
                    "projectname": Component(title="Projektname", value="Sachsen_GenericEntity"),
                    "sitename": Component(title="IfcSite", value="Sachsen_Site"),
                    "buildingname": Component(title="IfcBuilding", value="Sachsen_Tile"),
                },
            )
        ],
    )

    # --- 1. Parse ---
    logger.info("Parsing CityGML %s…", f"(filter: {BUILDING_ID})" if BUILDING_ID else "(all buildings)")
    t_parse = time.perf_counter()
    buildings = parse_typed_gml_files(
        [GML_FILE],
        building_id_filter=BUILDING_ID,
        profile="1.0",
        log_boundary_kinds=LOG_BOUNDARY_KINDS,
    )
    logger.info("Parsed %d building(s) in %.2fs", len(buildings), time.perf_counter() - t_parse)

    if not buildings:
        msg = f"Building '{BUILDING_ID}' not found." if BUILDING_ID else "No buildings found."
        logger.error(msg)
        return

    if MAX_BUILDINGS is not None:
        buildings = buildings[:MAX_BUILDINGS]
        logger.info("Capped to %d building(s) (MAX_BUILDINGS=%d)", len(buildings), MAX_BUILDINGS)

    # --- 2. Build IFC (single file or batches) ---
    if BUILDING_ID or BATCH_SIZE is None or len(buildings) <= (BATCH_SIZE or len(buildings)):
        # Single file — no batching needed
        suffix = BUILDING_ID if BUILDING_ID else "all"
        output_path = PathConfig.OUTPUT / f"output_generic_entity_sachsen_{suffix}.ifc"
        logger.info("Building IFC (single file)…")
        t = time.perf_counter()
        result = CityGenericEntityApp.build_ifc(
            buildings,
            request_params=request_params,
            output_path=output_path,
            coordinate_system=CoordinateSystemTemplates.epsg_25833(),
            color=(1.0, 0.8, 0.4),
            export_quantity_sets=False,
        )
        elapsed = time.perf_counter() - t
        if result:
            logger.info("OK  %s  (%.2fs)", result, elapsed, extra={"debug_category": "success"})
        else:
            logger.error("FAIL  (%.2fs)", elapsed, extra={"debug_category": "error"})
    else:
        # Batched export — one IFC file per batch, memory freed between batches
        total = len(buildings)
        n_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        logger.info("Exporting %d buildings in %d batch(es) of %d…", total, n_batches, BATCH_SIZE)
        t_all = time.perf_counter()

        for i in range(n_batches):
            batch = buildings[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
            _build_batch(batch, batch_index=i + 1, request_params=request_params)
            gc.collect()

        logger.info(
            "All %d batch(es) done in %.2fs",
            n_batches,
            time.perf_counter() - t_all,
            extra={"debug_category": "success"},
        )


if __name__ == "__main__":
    main()
