"""
Example: Generic trees IFC (``TreesGenericApp`` pipeline)
=========================================================

Flow: tunable constants → ``list[TreeRecord]`` → ``TreesGenericApp.build_ifc``.

This example does **not** fetch data, use pandas, DGM elevation or coordinate
transformation: ``position`` is set directly in metres (same CRS the app uses
for the project, Gauss-Kruger Hamburg via ``IfcModelBuilder`` inside
``TreesGenericApp``).
"""

from __future__ import annotations

import logging
import math
from typing import Dict, List, Tuple

from ifcfactory import ureg
from pydantic import BaseModel

from BIMFabrikHH_core.apps.trees.generic import TreeRecord, TreesGenericApp
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

TRUNK_COLOR: Tuple[float, float, float] = (0.44, 0.27, 0.18)
CROWN_COLOR: Tuple[float, float, float] = (0.13, 0.50, 0.18)
LEVEL_OF_DETAIL: int = 2
TRUNK_SEGMENTS: int = 10
OUTPUT_FILENAME: str = "example_trees_generic.ifc"
NAME_PREFIX: str = ""


def _psets_for_tree(
    *,
    baumnummer: str,
    gattung_deutsch: str,
    art_baum: str,
    pflanzjahr: int,
    kronendurchmesser_m: float,
    stammumfang_m: float,
    strassenname: str,
) -> Dict[str, BaseModel]:
    """Build Pset models; trunk diameter from circumference (m) for ``stammdurchmesser``."""
    stammdurchmesser_m = (stammumfang_m / math.pi) if stammumfang_m > 0 else 0.05
    obj = Pset_Objektinformation_Tree(
        baumnummer=baumnummer,
        gattung_deutsch=gattung_deutsch,
        art_baum=art_baum,
        pflanzjahr=pflanzjahr,
        kronendurchmesser=ureg.Quantity(kronendurchmesser_m, "meter"),
        stammdurchmesser=ureg.Quantity(stammdurchmesser_m, "meter"),
    )
    bau = Pset_Bauwerk_Tree(strassenname=strassenname)
    return {"Pset_Objektinformation": obj, "Pset_Bauwerk": bau}


def build_example_tree_records() -> List[TreeRecord]:
    """Minimal hand-authored ``TreeRecord`` list (no API, no transforms)."""
    return [
        TreeRecord(
            name="Baum_001",
            position=(558_400.0, 5_927_500.0, 5.0),
            kronendurchmesser=4.0,
            stammdurchmesser=0.35,
            detail=LEVEL_OF_DETAIL,
            segments=TRUNK_SEGMENTS,
            psets=_psets_for_tree(
                baumnummer="001",
                gattung_deutsch="Eiche",
                art_baum="Quercus robur",
                pflanzjahr=1990,
                kronendurchmesser_m=4.0,
                stammumfang_m=1.1,
                strassenname="Beispielstraße A",
            ),
        ),
        TreeRecord(
            name="Baum_002",
            position=(558_408.0, 5_927_500.0, 5.0),
            kronendurchmesser=6.0,
            stammdurchmesser=0.45,
            detail=LEVEL_OF_DETAIL,
            segments=TRUNK_SEGMENTS,
            baumhoehe=12.0,
            psets=_psets_for_tree(
                baumnummer="002",
                gattung_deutsch="Buche",
                art_baum="Fagus sylvatica",
                pflanzjahr=1985,
                kronendurchmesser_m=6.0,
                stammumfang_m=1.4,
                strassenname="Beispielstraße B",
            ),
        ),
        TreeRecord(
            name="Baum_003",
            position=(558_416.0, 5_927_500.0, 5.0),
            kronendurchmesser=3.5,
            stammdurchmesser=0.30,
            detail=max(1, LEVEL_OF_DETAIL - 1),
            segments=8,
            psets=_psets_for_tree(
                baumnummer="003",
                gattung_deutsch="Linde",
                art_baum="Tilia cordata",
                pflanzjahr=2001,
                kronendurchmesser_m=3.5,
                stammumfang_m=0.9,
                strassenname="Beispielstraße C",
            ),
        ),
    ]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("Example: generic trees via TreesGenericApp (no fetch, no transform)")
    records = build_example_tree_records()
    logging.info("Built %d TreeRecord(s)", len(records))
    logging.info(
        "Colours: trunk=%s crown=%s | LOD=%s segments=%s",
        TRUNK_COLOR,
        CROWN_COLOR,
        LEVEL_OF_DETAIL,
        TRUNK_SEGMENTS,
    )

    out = TreesGenericApp.build_ifc(
        records,
        output_path=OUTPUT_FILENAME,
        include_property_sets=True,
        trunk_color=TRUNK_COLOR,
        crown_color=CROWN_COLOR,
        name_prefix=NAME_PREFIX,
        validate=True,
    )
    logging.info("Done. IFC path: %s", out)


if __name__ == "__main__":
    main()
