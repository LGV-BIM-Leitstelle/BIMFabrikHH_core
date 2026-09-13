"""Generic Baugrundaufschluss example (offline BoreholeML fixture).

Loads ``response_WFS_boreholes_generic.xml`` next to this script (a saved
Hamburg ``HH_WFS_BoreholeML3`` ``GetFeature`` response, so no live HTTP) and
writes ``example_boreholes_generic.ifc`` with one stacked cylinder per soil
layer in map metres.

Fetching is deliberately not part of the app: the API hands the parsed WFS
response to :func:`records_from_boreholeml`, this example reads the same XML
from disk.

Service reference: `HH_WFS_BoreholeML3
<https://geodienste.hamburg.de/HH_WFS_BoreholeML3?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities>`_.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.boreholes.generic import (
    BoreholesGenericApp,
    load_borehole_records,
)
from BIMFabrikHH_core.config import get_logger, setup_logging

logger = get_logger()

_FIXTURE_NAME = "response_WFS_boreholes_generic.xml"

# Must match the extent the fixture was fetched with: the bbox only positions
# the Projektnullpunkt, it does not select boreholes from the saved response.
_FIXTURE_BBOX = BoundingBoxParams(min_x=9.9861, min_y=53.4867, max_x=9.9872, max_y=53.4872)


def main() -> None:
    here = Path(__file__).resolve()
    fixture = here.parent / _FIXTURE_NAME
    if not fixture.is_file():
        logger.error(
            "Fixture missing: %s — place the BoreholeML GetFeature response next to this example.",
            fixture,
            extra={"debug_category": "error"},
        )
        sys.exit(1)

    records = load_borehole_records(fixture)
    if not records:
        logger.error("No borehole records parsed from fixture", extra={"debug_category": "error"})
        sys.exit(1)
    logger.info(
        "Loaded %d borehole(s) with %d layer(s) from fixture",
        len(records),
        sum(len(record.layers) for record in records),
    )

    container = Container(
        containerTitle="Projektinformationen",
        containerId="Projektinformationen",
        components={
            "project": Component(title="Projektname", value="Baugrundaufschluesse Hamburg"),
            "site": Component(title="IfcSite", value="Hamburg"),
            "building": Component(title="IfcBuilding", value="Innenstadt"),
        },
    )
    request_body = RequestParams(bbox=_FIXTURE_BBOX, containers=[container])
    output_file = here.parent / "example_boreholes_generic.ifc"

    logger.info("Building → %s", output_file.name)
    result = BoreholesGenericApp.build_ifc(
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
    setup_logging()
    main()
