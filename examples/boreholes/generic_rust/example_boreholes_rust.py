"""Rust Baugrundaufschluss example (``BoreholesRustApp``).

Same fixture, bbox and output CRS codes as
``boreholes/generic/example_boreholes_generic.py``. Python still parses the
saved BoreholeML response. Rust groups each borehole into one
``IfcElementAssembly`` and writes the cylinders and the groundwater square.

Writes one IFC per code in ``OUTPUT_EPSGS`` (``example_boreholes_rust_<epsg>.ifc``)
and checks it with ``ifcopenshell.validate``.

Needs ``bimfabrikhh_core_rs`` installed (``pip install bimfabrikhh-core-rs``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.boreholes import BoreholeMLProcessor, BoreholesRustApp
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.core.ogc_extractor import extract_project_info

logger = get_logger()

# The saved GetFeature response lives next to the generic example.
_FIXTURE = Path(__file__).resolve().parents[1] / "generic" / "response_WFS_boreholes_generic.xml"

# Must match the extent the fixture was fetched with: the bbox only positions
# the Projektnullpunkt, it does not select boreholes from the saved response.
_FIXTURE_BBOX = BoundingBoxParams(min_x=9.9861, min_y=53.4867, max_x=9.9872, max_y=53.4872)
# Horizontal part of the WFS default EPSG:5555.
SOURCE_EPSG = 25832
# ETRS89 / UTM zone 32N and ETRS89 / Gauss-Krueger zone 3 (Hamburg).
OUTPUT_EPSGS = (25832, 10285)


def main() -> None:
    if not _FIXTURE.is_file():
        logger.error("Fixture missing: %s", _FIXTURE, extra={"debug_category": "error"})
        sys.exit(1)

    records = BoreholeMLProcessor().from_file(_FIXTURE)
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
            "project": Component(title="IfcProject", value="Baugrundaufschluesse Hamburg"),
            "site": Component(title="IfcSite", value="Hamburg"),
            "building": Component(title="IfcBuilding", value="Innenstadt"),
        },
    )
    project_name, site_name, _ = extract_project_info([container])
    here = Path(__file__).resolve().parent
    for epsg in OUTPUT_EPSGS:
        request = RequestParams(bbox=_FIXTURE_BBOX, containers=[container], source_epsg=SOURCE_EPSG, output_epsg=epsg)
        output_file = here / f"example_boreholes_rust_{epsg}.ifc"
        logger.info("Building → %s", output_file.name)
        result = BoreholesRustApp.build_ifc(
            records,
            output_path=output_file,
            project_name=project_name,
            site_name=site_name,
            bbox_wgs84=request.bbox_as_wgs84_tuple,
            source_epsg=request.source_epsg,
            output_epsg=request.output_epsg,
            basepoint=request.basepoint_xyz,
        )
        if not result:
            logger.error("IFC build failed", extra={"debug_category": "error"})
            sys.exit(1)
        logger.info("OK → %s\n%s", result.name, result.parent, extra={"debug_category": "success"})
        subprocess.run([sys.executable, "-m", "ifcopenshell.validate", "--rules", str(result)], check=True)


if __name__ == "__main__":
    setup_logging()
    main()
