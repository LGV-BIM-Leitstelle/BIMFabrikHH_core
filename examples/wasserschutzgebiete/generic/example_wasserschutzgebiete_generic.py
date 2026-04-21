"""Generic Wasserschutzgebiete example (offline GeoJSON fixture).

Loads ``response_OGC_wasserschutzgebiete_generic.json`` next to this script (saved
Hamburg OGC API FeatureCollection in **EPSG:25832** polygon coordinates; no live HTTP)
and writes ``example_wasserschutzgebiete_generic.ifc`` with geometry in map metres.

API reference: `Wasserschutzgebiete Hamburg <https://api.hamburg.de/datasets/v1/wasserschutzgebiete/api?f=html>`_.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core import Component, Container, RequestParams
from BIMFabrikHH_core.apps.wasserschutzgebiete.generic import (
    WasserschutzgebieteGenericApp,
    load_wasserschutzgebiete_records,
)
from BIMFabrikHH_core.config import get_logger

logger = get_logger()

_FIXTURE_NAME = "response_OGC_wasserschutzgebiete_generic.json"


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

    records = load_wasserschutzgebiete_records(fixture)
    logger.info("Loaded %d Wasserschutzgebiet feature(s) from fixture", len(records))
    records = records[:1]
    if not records:
        logger.error("No records after slice", extra={"debug_category": "error"})
        sys.exit(1)
    logger.info("Using first feature only → %d record(s) for IFC", len(records))

    container = Container(
        containerTitle="Wasserschutzgebiete_Container",
        containerId="wasserschutzgebiete_standard",
        components={
            "description": Component(title="Description", value="Hamburg Wasserschutzgebiete (OGC API)"),
            "type": Component(title="Model Type", value="Extruded Schutzzonen"),
        },
    )
    request_body = RequestParams(containers=[container])
    output_file = here.parent / "example_wasserschutzgebiete_generic.ifc"

    logger.info("Building → %s", output_file.name)
    result = WasserschutzgebieteGenericApp.build_ifc(
        records,
        request_params=request_body,
        output_path=output_file,
    )
    if not result:
        logger.error("IFC build failed", extra={"debug_category": "error"})
        sys.exit(1)
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
    main()
