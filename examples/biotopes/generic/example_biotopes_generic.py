"""Generic Biotopes example (offline GeoJSON fixtures).

TODO complete the docstring.

Loads the Hamburg OGC API FeatureCollections with **EPSG:25832**
``response_OGC_flaechenhafte_biotope_nicht_geschuetzt.json``,
``response_OGC_flaechenhafte_biotope_geschuetzt.json``,
``response_OGC_linienhafte_biotope_nicht_geschuetzt.json``,
``response_OGC_linienhafte_biotope_geschuetzt.json``,
``response_OGC_punkthafte_biotope_nicht_geschuetzt.json``,
``response_OGC_punkthafte_biotope_geschuetzt.json``
(files have to be placed next to this script) and writes ``<input file name>_<epsg>.ifc`` per code in ``OUTPUT_EPSGS``
with biotopes as 30 m ``IfcBuildingElementProxy`` volumes standing on ``z = 0``.
In the IFC results, area biotopes are represented as filled polygones,
line biotopes have a thickness of record.breite_lineares_objekt (or 1 m if None)
and point biotopes are represented as 5m x 5m boxes, all with
geometry in map metres of that CRS.

API references:
https://api.hamburg.de/datasets/v1/biotopkataster/api?f=html
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.biotopes.generic import BiotopesGenericApp, load_biotope_records
from BIMFabrikHH_core.config import get_logger, setup_logging

logger = get_logger()

# CRS of the fixture coordinates (``crs=`` of the OGC request).
SOURCE_EPSG = 25832
# ETRS89 / UTM zone 32N and ETRS89 / Gauss-Krueger zone 3 (Hamburg).
OUTPUT_EPSGS = (25832, 10285)


EXAMPLES = [
    ("response_OGC_flaechenhafte_biotope_nicht_geschuetzt.json", False, (9.9309, 53.5609, 9.9460, 53.6162)),
    ("response_OGC_flaechenhafte_biotope_geschuetzt.json", True, (9.8775, 53.6050, 9.9273, 53.6237)),
    ("response_OGC_linienhafte_biotope_nicht_geschuetzt.json", False, (9.7809, 53.4938, 9.8861, 53.6055)),
    ("response_OGC_linienhafte_biotope_geschuetzt.json", True, (9.9346, 53.4734, 10.1619, 53.6083)),
    ("response_OGC_punkthafte_biotope_nicht_geschuetzt.json", False, (9.8170, 53.4412, 10.1590, 53.6702)),
    ("response_OGC_punkthafte_biotope_geschuetzt.json", True, (9.8961, 53.4365, 10.1469, 53.6821)),
]


def main() -> None:
    examples_dir = Path(__file__).resolve().parent

    for fixture_name, is_protected, bbox in EXAMPLES:
        input_file = examples_dir / fixture_name
        if not input_file.is_file():
            logger.error(
                "Fixture missing: %s — place the OGC FeatureCollection JSON files next to this example.",
                input_file,
                extra={"debug_category": "error"},
            )
            sys.exit(1)

        min_x, min_y, max_x, max_y = bbox

        if min_x >= max_x or min_y >= max_y:
            logger.error(
                "Invalid bounding box: minimum coordinates must be less than maximum coordinates.",
                extra={"debug_category": "error"},
            )
            sys.exit(2)

        bbox_params = BoundingBoxParams(
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )

        generate_ifc_from_biotope_json(input_file, bbox_params, is_protected)


def generate_ifc_from_biotope_json(input_file: Path, bbox: BoundingBoxParams, is_protected: bool) -> None:

    records = load_biotope_records(input_file, is_protected=is_protected)
    logger.info("Loaded %d biotope feature(s) from %s", len(records), input_file)

    if not records:
        logger.error(
            "No records parsed from input JSON",
            extra={"debug_category": "error"},
        )
        sys.exit(1)

    logger.info("Bounding box: min_x=%s, min_y=%s, max_x=%s, max_y=%s", bbox.min_x, bbox.min_y, bbox.max_x, bbox.max_y)

    total_area = sum(rec.flaeche_oder_laenge or 0.0 for rec in records)
    logger.info("Amtliche Fläche total: %.0f m²", total_area)

    container = Container(
        containerTitle="Biotope_Container",
        containerId="biotope_standard",
        components={
            "description": Component(
                title="Description",
                value="Hamburg Biotopkataster (OGC API)",
            ),
            "type": Component(
                title="Model Type",
                value="Extruded Biotopes as IfcBuildingElementProxy",
            ),
        },
    )

    for output_epsg in OUTPUT_EPSGS:
        request_body = RequestParams(
            bbox=bbox, containers=[container], source_epsg=SOURCE_EPSG, output_epsg=output_epsg
        )

        output_file = input_file.with_name(f"{input_file.stem}_{output_epsg}.ifc")

        logger.info("Building → %s", output_file.name)

        start = time.perf_counter()

        result = BiotopesGenericApp.build_ifc(
            records,
            request_params=request_body,
            output_path=output_file,
        )

        elapsed = time.perf_counter() - start

        if not result:
            logger.error("IFC build failed", extra={"debug_category": "error"})
            sys.exit(1)

        logger.info("TIMING Biotopes EPSG:%d: %.3f s → %s", output_epsg, elapsed, result.name)
        logger.info(
            "OK → %s\n%s",
            result.name,
            result.parent,
            extra={"debug_category": "success"},
        )

        subprocess.run(
            [
                sys.executable,
                "-m",
                "ifcopenshell.validate",
                "--rules",
                str(result),
            ],
            check=True,
        )


if __name__ == "__main__":
    setup_logging()
    main()
