"""
Example: Generic trees IFC (``TreesGenericApp`` pipeline)
=========================================================

Flow: tunable constants → ``list[TreeRecord]`` → ``TreesGenericApp.build_ifc``.

This example does **not** fetch cadastral data or use pandas. It places
``N_TREES`` random trunks in the same Innenstadt / Alster crop as
``examples/terrain/generic`` (EPSG:25832), so the tree IFC and
``example_dgm_generic.ifc`` overlay.

Set ``USE_DGM = False`` to keep the hand-written Z and skip raster
sampling; with it on, Z comes from the DGM1 tiles covering that crop.

One IFC is written per code in ``OUTPUT_EPSGS`` (``example_trees_generic_<epsg>.ifc``):
the records are in ``SOURCE_EPSG`` and the app transforms them into each output CRS.
"""

from __future__ import annotations

import logging
import math
import random
from datetime import date
from typing import List, Sequence, Tuple

from BIMFabrikHH_core.apps.trees import build_tree_psets, calculate_tree_trunk_height, full_tree_height
from BIMFabrikHH_core.apps.trees.generic import TreeRecord, TreesGenericApp
from BIMFabrikHH_core.config import setup_logging
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832

TRUNK_COLOR: Tuple[float, float, float] = (0.44, 0.27, 0.18)
CROWN_COLOR: Tuple[float, float, float] = (0.13, 0.50, 0.18)
LEVEL_OF_DETAIL: int = 2
TRUNK_SEGMENTS: int = 10
OUTPUT_FILENAME: str = "example_trees_generic_{epsg}.ifc"
# The random positions are drawn in ETRS89 / UTM zone 32N, like the Hamburg services.
SOURCE_EPSG: int = 25832
# ETRS89 / UTM zone 32N and ETRS89 / Gauss-Krueger zone 3 (Hamburg).
OUTPUT_EPSGS: Tuple[int, ...] = (25832, 10285)
NAME_PREFIX: str = ""
USE_DGM: bool = True
N_TREES: int = 50
RANDOM_SEED: int = 42
# Keep trunks on the mesh, not on the crop edge.
BBOX_MARGIN_M: float = 40.0
# Same Innenstadt / Alster crop as ``examples/terrain/generic`` so the two
# IFCs share CRS, bbox and Nullpunkt and can be opened together.
BBOX_WGS84 = (9.9769, 53.5478, 9.991435, 53.55622)
DGM_FOLDER = PathConfig.ASSETS / "dgm1_hh_2022-04-30"
_E0, _N0, _E1, _N1 = bbox_wgs84_to_epsg25832(BBOX_WGS84)
_SPECIES: Sequence[Tuple[str, str]] = (
    ("Eiche", "Quercus robur"),
    ("Buche", "Fagus sylvatica"),
    ("Linde", "Tilia cordata"),
    ("Ahorn", "Acer platanoides"),
    ("Birke", "Betula pendula"),
)


def build_example_tree_records() -> List[TreeRecord]:
    """``N_TREES`` random records inside the generic DGM crop (fixed seed).

    The trunk height follows :func:`calculate_tree_trunk_height` — a measured
    trunk height clamped to 1.10 m, else 0.85 x Kronendurchmesser — and
    :func:`full_tree_height` turns it into the Gesamthöhe published as
    ``_Baumhoehe``. The "measured" heights here are random demo values so both
    branches end up in the IFC: every fourth tree is estimated, the rest are
    marked "gemessen". Real Strassenbaumkataster data has no height attribute,
    so every Kataster tree is estimated.
    """
    rng = random.Random(RANDOM_SEED)
    aufnahmedatum = date.today().isoformat()
    records: List[TreeRecord] = []
    for i in range(1, N_TREES + 1):
        x = rng.uniform(_E0 + BBOX_MARGIN_M, _E1 - BBOX_MARGIN_M)
        y = rng.uniform(_N0 + BBOX_MARGIN_M, _N1 - BBOX_MARGIN_M)
        kronendurchmesser = rng.uniform(3.0, 12.0)
        stammumfang = rng.uniform(0.6, 2.2)
        stammdurchmesser = stammumfang / math.pi
        gattung, art = rng.choice(_SPECIES)
        measured_height = None if i % 4 == 0 else rng.uniform(8.0, 22.0)
        stammhoehe_m, stammhoehe_bemerkung = calculate_tree_trunk_height(
            kronendurchmesser=kronendurchmesser,
            stammhoehe=measured_height,
        )
        gesamthoehe_m, gesamthoehe_bemerkung = full_tree_height(
            stammhoehe_m, kronendurchmesser, stammhoehe_bemerkung
        )
        baumnummer = f"{i:03d}"
        records.append(
            TreeRecord(
                name=f"Baum_{baumnummer}",
                position=(x, y, 5.0),
                kronendurchmesser=kronendurchmesser,
                stammdurchmesser=stammdurchmesser,
                detail=LEVEL_OF_DETAIL,
                segments=TRUNK_SEGMENTS,
                baumhoehe=stammhoehe_m,
                psets=build_tree_psets(
                    baumnummer=baumnummer,
                    gattung=gattung,
                    art=art,
                    pflanzjahr=rng.randint(1960, 2018),
                    kronendurchmesser_m=kronendurchmesser,
                    stammdurchmesser_m=stammdurchmesser,
                    baumhoehe_m=gesamthoehe_m,
                    baumhoehe_bemerkung=gesamthoehe_bemerkung,
                    aufnahmedatum=aufnahmedatum,
                    strasse="Beispielstraße",
                ),
            )
        )
    return records


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logging.info("Example: generic trees via TreesGenericApp (no fetch)")
    records = build_example_tree_records()
    logging.info("Built %d TreeRecord(s)", len(records))
    logging.info(
        "Colours: trunk=%s crown=%s | LOD=%s segments=%s",
        TRUNK_COLOR,
        CROWN_COLOR,
        LEVEL_OF_DETAIL,
        TRUNK_SEGMENTS,
    )

    tif_files = sorted(DGM_FOLDER.glob("*.tif")) if USE_DGM else None
    logging.info(
        "DGM drape: %s",
        f"{len(tif_files)} tile(s) in {DGM_FOLDER}" if tif_files else "off (hand-written Z)",
    )

    for epsg in OUTPUT_EPSGS:
        out = TreesGenericApp.build_ifc(
            records,
            output_path=OUTPUT_FILENAME.format(epsg=epsg),
            include_property_sets=True,
            trunk_color=TRUNK_COLOR,
            crown_color=CROWN_COLOR,
            name_prefix=NAME_PREFIX,
            validate=True,
            bbox_wgs84=BBOX_WGS84,
            tif_files=tif_files,
            source_epsg=SOURCE_EPSG,
            output_epsg=epsg,
        )
        logging.info("Done. EPSG:%d IFC path: %s", epsg, out)


if __name__ == "__main__":
    setup_logging()
    main()
