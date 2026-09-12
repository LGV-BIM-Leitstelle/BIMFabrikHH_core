"""Rust trees example (``TreesRustApp`` pipeline).

Same records, bbox and DGM tiles as ``trees/generic/example_trees_generic.py``
— ``N_TREES`` random trunks in the Innenstadt / Alster crop — but the IFC is
written by Rust via ``bimfabrikhh_core_rs.trees_to_ifc`` instead of the
ifcfactory writer. Python still prepares the records and drapes Z.

Because both examples share bbox and Nullpunkt, the output opens together
with ``terrain/generic/example_dgm_generic.ifc`` and with the ifcfactory
tree IFC.

Needs ``bimfabrikhh_core_rs`` installed (``pip install bimfabrikhh-core-rs``).
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

from BIMFabrikHH_core.apps.trees.generic_rust import TreesRustApp
from BIMFabrikHH_core.config import setup_logging

# Reuse the record builder and crop from the generic example (sibling folder).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "generic"))
from example_trees_generic import (  # noqa: E402
    BBOX_WGS84,
    DGM_FOLDER,
    USE_DGM,
    build_example_tree_records,
)

OUTPUT_FILENAME: str = "example_trees_rust.ifc"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("Example: trees via TreesRustApp (bimfabrikhh_core_rs writer)")
    records = build_example_tree_records()
    logging.info("Built %d TreeRecord(s)", len(records))

    tif_files = sorted(DGM_FOLDER.glob("*.tif")) if USE_DGM else None
    logging.info(
        "DGM drape: %s",
        f"{len(tif_files)} tile(s) in {DGM_FOLDER}" if tif_files else "off (hand-written Z)",
    )

    start = time.perf_counter()
    # Colours stay at the Rust defaults: that writer expects 0-255 RGB,
    # while the ifcfactory example uses normalized 0-1 floats.
    out = TreesRustApp.build_ifc(
        records,
        output_path=Path(__file__).parent / OUTPUT_FILENAME,
        include_property_sets=True,
        bbox_wgs84=BBOX_WGS84,
        tif_files=tif_files,
    )
    logging.info("TIMING trees (Rust): %.3f s", time.perf_counter() - start)
    logging.info("Done. IFC path: %s", out)


if __name__ == "__main__":
    setup_logging()
    main()
