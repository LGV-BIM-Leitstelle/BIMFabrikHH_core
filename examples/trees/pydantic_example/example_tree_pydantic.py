"""
Example: Pydantic tree IFC (``BaumPydanticApp`` pipeline)
======================================================

Flow: tunable constants → list of tree dicts → ``BaumPydanticApp.build_ifc_from_tree_data``.

This example does **not** fetch data, use pandas, DGM elevation, or coordinate
transformation: ``position`` is set directly in metres (same CRS the app uses
for the project, Gauss-Kruger Hamburg via ``IfcModelBuilder`` inside
``BaumPydanticApp``).
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Tuple

from ifcfactory import ureg

from BIMFabrikHH_core.apps.trees.generic.app_pydantic import BaumPydanticApp
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

# --- Tunable constants -------------------------------------------------------

TRUNK_COLOR: Tuple[float, float, float] = (0.44, 0.27, 0.18)
CROWN_COLOR: Tuple[float, float, float] = (0.13, 0.50, 0.18)
LEVEL_OF_DETAIL: int = 2
TRUNK_SEGMENTS: int = 10
OUTPUT_FILENAME: str = "example_tree_pydantic.ifc"
# Optional prefix for IFC tree names (e.g. project or site); empty keeps names like Baum_001.
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
) -> Dict[str, Any]:
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


def build_example_tree_data() -> List[Dict[str, Any]]:
    """
    Minimal hand-authored rows (no API, no transforms).

    Each dict matches ``BaumPydanticApp.build_ifc_from_tree_data`` expectations.
    """
    return [
        {
            "name": "Baum_001",
            "position": (558_400.0, 5_927_500.0, 5.0),
            "kronendurchmesser": 4.0,
            "stammdurchmesser": 0.35,
            "detail": LEVEL_OF_DETAIL,
            "segments": TRUNK_SEGMENTS,
            "psets": _psets_for_tree(
                baumnummer="001",
                gattung_deutsch="Eiche",
                art_baum="Quercus robur",
                pflanzjahr=1990,
                kronendurchmesser_m=4.0,
                stammumfang_m=1.1,
                strassenname="Beispielstraße A",
            ),
        },
        {
            "name": "Baum_002",
            "position": (558_408.0, 5_927_500.0, 5.0),
            "kronendurchmesser": 6.0,
            "stammdurchmesser": 0.45,
            "detail": LEVEL_OF_DETAIL,
            "segments": TRUNK_SEGMENTS,
            "baumhoehe": 12.0,
            "psets": _psets_for_tree(
                baumnummer="002",
                gattung_deutsch="Buche",
                art_baum="Fagus sylvatica",
                pflanzjahr=1985,
                kronendurchmesser_m=6.0,
                stammumfang_m=1.4,
                strassenname="Beispielstraße B",
            ),
        },
        {
            "name": "Baum_003",
            "position": (558_416.0, 5_927_500.0, 5.0),
            "kronendurchmesser": 3.5,
            "stammdurchmesser": 0.30,
            "detail": max(1, LEVEL_OF_DETAIL - 1),
            "segments": 8,
            "psets": _psets_for_tree(
                baumnummer="003",
                gattung_deutsch="Linde",
                art_baum="Tilia cordata",
                pflanzjahr=2001,
                kronendurchmesser_m=3.5,
                stammumfang_m=0.9,
                strassenname="Beispielstraße C",
            ),
        },
    ]


def validate_example_tree_data(tree_data: List[Dict[str, Any]]) -> None:
    """Lightweight checks only (no pandas). Raises ``ValueError`` on failure."""
    if not tree_data:
        raise ValueError("tree_data is empty")

    required = (
        "name",
        "position",
        "kronendurchmesser",
        "stammdurchmesser",
        "detail",
        "segments",
        "psets",
    )

    for i, row in enumerate(tree_data):
        label = row.get("name", f"index_{i}")
        for key in required:
            if key not in row:
                raise ValueError(f"{label}: missing required key {key!r}")

        pos = row["position"]
        if not isinstance(pos, (tuple, list)) or len(pos) != 3:
            raise ValueError(f"{label}: position must be a 3-tuple")

        for k in ("kronendurchmesser", "stammdurchmesser"):
            v = row[k]
            if not isinstance(v, (int, float)) or v < 0:
                raise ValueError(f"{label}: invalid {k}: {v!r}")

        d, s = row["detail"], row["segments"]
        if not isinstance(d, int) or not (1 <= d <= 4):
            raise ValueError(f"{label}: detail must be int 1..4, got {d!r}")
        if not isinstance(s, int) or s < 3:
            raise ValueError(f"{label}: segments must be int >= 3, got {s!r}")

        psets = row["psets"]
        if not isinstance(psets, dict) or not psets:
            raise ValueError(f"{label}: psets must be a non-empty dict")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("Example: pydantic trees via BaumPydanticApp (no fetch, no transform)")
    tree_data = build_example_tree_data()
    validate_example_tree_data(tree_data)

    logging.info("Validated %d tree row(s)", len(tree_data))
    logging.info(
        "Colours: trunk=%s crown=%s | LOD=%s segments=%s",
        TRUNK_COLOR,
        CROWN_COLOR,
        LEVEL_OF_DETAIL,
        TRUNK_SEGMENTS,
    )

    out = BaumPydanticApp.build_ifc_from_tree_data(
        tree_data,
        output_path=OUTPUT_FILENAME,
        include_property_sets=True,
        trunk_color=TRUNK_COLOR,
        crown_color=CROWN_COLOR,
        name_prefix=NAME_PREFIX,
    )
    logging.info("Done. IFC path: %s", out)


if __name__ == "__main__":
    main()
