"""Generic Flurstuecke example (offline GeoJSON fixture).

Loads ``response_OGC_flurstuecke_generic.json`` next to this script and writes
``example_flurstuecke_generic.ifc`` with the parcels as 30 m ``IfcBuildingElementProxy``
volumes standing on ``z = 0``, geometry in map metres.

The fixture is a saved Hamburg OGC API FeatureCollection with **EPSG:25832**
``MultiPolygon`` coordinates — no live HTTP from ``BIMFabrikHH_core``. It holds
all 779 ALKIS parcels of the DGM example bbox (Innenstadt /
Binnenalster–Außenalster), the same crop as the generic terrain and streets
examples, so the parcels overlay the DGM output of
``examples/terrain/generic/example_generic_terrain_guided.py``.

The live request will move to ``bimfabrikapi``; to refresh the fixture by hand,
page through ``limit`` / ``offset`` (the API caps a page at 500 features)::

    curl -G "https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Flurstueck/items" \\
      --data-urlencode "f=json" \\
      --data-urlencode "bbox=9.9769,53.5478,9.991435,53.55622" \\
      --data-urlencode "crs=http://www.opengis.net/def/crs/EPSG/0/25832" \\
      --data-urlencode "limit=500" --data-urlencode "offset=0"

API reference: `ALKIS vereinfacht Hamburg
<https://api.hamburg.de/datasets/v1/alkis_vereinfacht/api?f=html>`_.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.flurstuecke.generic import (
    FlurstueckeGenericApp,
    load_flurstuecke_records,
)
from BIMFabrikHH_core.config import get_logger, setup_logging

logger = get_logger()

_FIXTURE_NAME = "response_OGC_flurstuecke_generic.json"

# Same crop as ``examples/terrain/generic/local_dgm.py`` EXAMPLE_BBOX.
_EXAMPLE_BBOX = BoundingBoxParams(min_x=9.9769, min_y=53.5478, max_x=9.991435, max_y=53.55622)


def main() -> None:
    here = Path(__file__).resolve()
    fixture = here.parent / _FIXTURE_NAME
    if not fixture.is_file():
        logger.error(
            "Fixture missing: %s — place the OGC FeatureCollection JSON next to this example.",
            fixture,
            extra={"debug_category": "error"},
        )
        sys.exit(1)

    records = load_flurstuecke_records(fixture)
    logger.info("Loaded %d Flurstueck feature(s) from fixture", len(records))
    if not records:
        logger.error("No records parsed from fixture", extra={"debug_category": "error"})
        sys.exit(1)
    gemarkungen = sorted({rec.gemarkung for rec in records if rec.gemarkung})
    total_area = sum(rec.flaeche or 0.0 for rec in records)
    logger.info("Gemarkung(en): %s", ", ".join(gemarkungen))
    logger.info("Amtliche Fläche total: %.0f m²", total_area)
    for rec in records[:3]:
        logger.info("  %s | %s | %.0f m² | %s", rec.flstkennz, rec.gemarkung, rec.flaeche or 0.0, rec.lagebeztxt)

    container = Container(
        containerTitle="Flurstuecke_Container",
        containerId="flurstuecke_standard",
        components={
            "description": Component(title="Description", value="Hamburg ALKIS Flurstuecke (OGC API)"),
            "type": Component(title="Model Type", value="Extruded Flurstuecke as IfcBuildingElementProxy"),
        },
    )
    request_body = RequestParams(bbox=_EXAMPLE_BBOX, containers=[container])
    output_file = here.parent / "example_flurstuecke_generic.ifc"

    logger.info("Building → %s", output_file.name)
    start = time.perf_counter()
    result = FlurstueckeGenericApp.build_ifc(
        records,
        request_params=request_body,
        output_path=output_file,
    )
    elapsed = time.perf_counter() - start
    if not result:
        logger.error("IFC build failed", extra={"debug_category": "error"})
        sys.exit(1)
    logger.info("TIMING Flurstuecke: %.3f s  → %s", elapsed, result.name)
    logger.info(
        "OK → %s\n%s",
        result.name,
        result.parent,
        extra={"debug_category": "success"},
    )
    subprocess.run(
        [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(result)],
        check=True,
    )


if __name__ == "__main__":
    setup_logging()
    main()
