"""Frontend workflows end to end, with a Nullpunktobjekt check (offline).

Runs the BIM-Portal workflows with the apps of the ``BIMFabrikHH_api``
processes, each as generic (ifcfactory) and, where one exists, Rust variant:

=======================  ===========================  ==========================
Workflow (portal JSON)   generic                      rust (``-rs`` process)
=======================  ===========================  ==========================
Nullpunkt                ``place_basepoint``          ``write_ifc``
001 Baumkataster         ``TreesGenericApp``          ``TreesRustApp``
002 Gelaendemodell       ``TerrainGenericApp``        ``TerrainRustApp``
003 Stadtmodell          ``CityGenericApp``           ``CityRustApp``
004 Flurstuecke          ``FlurstueckeGenericApp``    -
005 Bohrungen            ``BoreholesGenericApp``      -
=======================  ===========================  ==========================

The Gelaendemodell runs as Typ 1 and as Typ 2 (ALKIS Nutzung Bruchkanten).
``nullpunkt`` writes only the Nullpunktobjekt (no Fachdaten, no input files) at the
``UMRING`` lower-left, generic with ifcfactory and Rust with ``write_ifc``.
The portal frontend calls the Rust variant for 001-003.

Each request carries the portal form containers (``Pset_Georeferenzierung``,
``Pset_Objektinformation``, ``Pset_Modellinformation``, ``Pset_Hyperlink``)
with the field titles the portal sends, including the lowercase
``_Hyperlink_001_bemerkung``. ``_ArtFachmodell`` / ``_ArtTeilmodell`` /
``_GemObjektkatalog`` follow the BIM.Hamburg Objektkatalog.

After each build the Nullpunktobjekt is read back and its psets are compared
with the request. The summary lists every deviation per run; the script exits
with code 1 if there is one.

All runs use the same ~500 m x 500 m Umring (0.25 km²), so the IFCs overlay.
Inputs are local, no network:

* DGM1 and LoD2 tiles in ``PathConfig.ASSETS``
* trees, Flurstuecke, ALKIS Nutzung and boreholes in ``data/`` (they cover
  ``UMRING``; download them again after changing it)

The Rust variants need ``bimfabrikhh_core_rs`` (``pip install bimfabrikhh-core-rs``).

Usage::

    python workflows.py                 # all workflows
    python workflows.py --list          # workflow keys
    python workflows.py 003 rust        # keys containing "003" or "rust"
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from dataclasses import dataclass
from datetime import date
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import ifcopenshell
import ifcopenshell.util.element

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, PathConfig, RequestParams
from BIMFabrikHH_core.apps.boreholes import BoreholeMLProcessor, BoreholesGenericApp
from BIMFabrikHH_core.apps.city import CityGenericApp, CityRustApp
from BIMFabrikHH_core.apps.flurstuecke.generic import FlurstueckeGenericApp, load_flurstuecke_records
from BIMFabrikHH_core.apps.terrain.generic import TerrainGenericApp
from BIMFabrikHH_core.apps.terrain.generic_rust import TerrainRustApp
from BIMFabrikHH_core.apps.trees.column_schema import DEFAULT_OAF_SCHEMA
from BIMFabrikHH_core.apps.trees.generic import TreesGenericApp
from BIMFabrikHH_core.apps.trees.generic_rust import TreesRustApp
from BIMFabrikHH_core.apps.trees.processing import dataframe_to_records
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.core.data_processing import DataProcessor
from BIMFabrikHH_core.core.geometry import basepoint_pset_values, basepoint_xyz, place_basepoint
from BIMFabrikHH_core.core.georeferencing import DGM_TILE_VERTICAL_EPSG, CoordinateTransformer
from BIMFabrikHH_core.core.model_creator import georeference_options, init_ifc_project, output_coordinate_system
from BIMFabrikHH_core.core.ogc_extractor import extract_psets_basepoint
from BIMFabrikHH_core.data_models.streets import GUIDE_NUTZARTEN, records_from_geojson_feature_collection

_HERE = Path(__file__).resolve().parent

# Reuse the DGM tile resolver of the terrain examples (sibling folder).
sys.path.insert(0, str(_HERE.parent / "terrain" / "generic"))
from local_dgm import dgm_tile_paths  # noqa: E402

logger = get_logger()

# One Umring for all workflows (Innenstadt / Alster, ~500 m x 500 m = 0.25 km²),
# inside the local DGM1 and LoD2 tiles.
UMRING = BoundingBoxParams(min_x=9.9804, min_y=53.5513, max_x=9.9880, max_y=53.5558)

DATA_DIR = _HERE / "data"
TREES_FILE = "trees_oaf.json"
FLURSTUECKE_FILE = "flurstuecke_oaf.json"
NUTZUNG_FILE = "alkis_nutzung_oaf.json"
BOREHOLES_FILE = "boreholes_wfs.xml.gz"
# LoD2, the portal's default Level Of Geometry for the Stadtmodell.
CITY_TILES = ["LoD2_32_564_5934_1_HH.xml", "LoD2_32_565_5934_1_HH.xml"]

# Edge length of the standalone Nullpunktobjekt, as in the Stadtmodell.
NULLPUNKT_SIZE = 8.0

# CRS per input, as in BIMFabrikHH_api: OAF responses, tiles and the borehole
# WFS are EPSG:25832; tiles have DHHN2016 heights, the WFS DHHN92 (EPSG:5783).
SOURCE_EPSG = 25832
BOREHOLES_VERTICAL_EPSG = 5783

# Same author as the IFC header (FILE_NAME, IfcPerson, IfcOrganization).
ERSTELLER = "BIM-Leitstelle, LGV Hamburg"
HYPERLINK = "www.bim.hamburg.de"
HYPERLINK_BEMERKUNG = "Link zur Homepage von BIM.Hamburg"

Run = Callable[[List[Container], Path], Optional[Path]]


@dataclass(frozen=True)
class Workflow:
    key: str
    art_fachmodell: str
    art_teilmodell: str
    gem_objektkatalog: str
    run: Run

    @property
    def output(self) -> Path:
        return _HERE / f"example_workflow_{self.key}.ifc"


def form_containers(workflow: Workflow) -> List[Container]:
    """Containers as the portal form submits them (machineName keys, field titles)."""
    return [
        Container(
            containerTitle="Projektinformationen",
            containerId="Projektinformationen",
            components={
                "projectname": Component(title="IfcProject", value=f"Workflow {workflow.key}"),
                "ifc_site": Component(title="IfcSite", value="Hamburg"),
                "ifc_building": Component(title="IfcBuilding", value=workflow.art_teilmodell),
            },
        ),
        Container(
            containerTitle="Pset_Georeferenzierung",
            containerId="Pset_Georeferenzierung",
            components={
                "hoehenstatus": Component(title="_Hoehenstatus", value="HS170"),
                "hoehensystem": Component(title="_Hoehensystem", value="DHHN2016"),
                "koordinatensystem": Component(title="_Koordinatensystem", value="ETRS89-UTM32N"),
                "lagestatus": Component(title="_Lagestatus", value="LS310"),
            },
        ),
        Container(
            containerTitle="Pset_Objektinformation",
            containerId="Pset_Objektinformation",
            components={
                "idebene1": Component(title="_IDEbene1", value="Nullpunktobjekt"),
                "idebene2": Component(title="_IDEbene2", value="Nullpunktobjekt"),
                "idebene3": Component(title="_IDEbene3", value="Nullpunktobjekt"),
            },
        ),
        Container(
            containerTitle="Pset_Modellinformation",
            containerId="Pset_Modellinformation",
            components={
                "_artfachmodell": Component(title="_ArtFachmodell", value=workflow.art_fachmodell),
                "_artteilmodell": Component(title="_ArtTeilmodell", value=workflow.art_teilmodell),
                "auftraggeber": Component(title="_Auftraggeber", value="LGV"),
                "ersteller": Component(title="_Ersteller", value=ERSTELLER),
                "erstelldatum": Component(title="_Erstelldatum", value=date.today().isoformat()),
                "gemobjektkatalog": Component(title="_GemObjektkatalog", value=workflow.gem_objektkatalog),
                "projektname": Component(title="_Projektname", value=f"Workflow {workflow.key}"),
                "projektnummer": Component(title="_Projektnummer", value="12345"),
            },
        ),
        Container(
            containerTitle="Pset_Hyperlink",
            containerId="Pset_Hyperlink",
            components={
                "hyperlink1": Component(title="_Hyperlink_001", value=HYPERLINK),
                "hyperlink1bem": Component(title="_Hyperlink_001_bemerkung", value=HYPERLINK_BEMERKUNG),
            },
        ),
    ]


def _load_json(name: str) -> Dict[str, Any]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def _request(containers: List[Container], vertical_epsg: Optional[int] = None) -> RequestParams:
    return RequestParams(bbox=UMRING, containers=containers, source_epsg=SOURCE_EPSG, vertical_epsg=vertical_epsg)


def run_nullpunkt(containers: List[Container], output: Path, rust: bool) -> Optional[Path]:
    """Only the Nullpunktobjekt at the ``UMRING`` lower-left, with the form psets."""
    transformer = CoordinateTransformer.from_source_to_output(SOURCE_EPSG, None, DGM_TILE_VERTICAL_EPSG)
    bbox_wgs84 = (UMRING.min_x, UMRING.min_y, UMRING.max_x, UMRING.max_y)
    psets = extract_psets_basepoint(containers)
    if rust:
        from bimfabrikhh_core_rs import write_ifc

        written = write_ifc(
            [],
            str(output),
            project_name="Nullpunkt_Project",
            site_name="Nullpunkt_Site",
            crs=output_coordinate_system(transformer),
            basepoint=basepoint_xyz(bbox_wgs84=bbox_wgs84, transformer=transformer),
            basepoint_size=NULLPUNKT_SIZE,
            basepoint_psets=basepoint_pset_values(psets),
        )
        return Path(written)
    builder = init_ifc_project(
        project_name="Nullpunkt_Project", site_name="Nullpunkt_Site", **georeference_options(transformer)
    )
    place_basepoint(
        model=builder.model,
        site=builder.site,
        bbox_wgs84=bbox_wgs84,
        size=NULLPUNKT_SIZE,
        psets=psets,
        transformer=transformer,
    )
    return Path(str(builder.save_ifc_to_output(output.name, output_path=output)))


def run_trees(containers: List[Container], output: Path, rust: bool) -> Optional[Path]:
    records = dataframe_to_records(
        DataProcessor.raw_data_to_dataframe(_load_json(TREES_FILE)),
        aufnahmedatum=date.today().isoformat(),
        schema=DEFAULT_OAF_SCHEMA,
        source_name="workflows",
    )
    logger.info("  %d tree(s)", len(records))
    common = dict(
        output_path=output,
        bbox_wgs84=(UMRING.min_x, UMRING.min_y, UMRING.max_x, UMRING.max_y),
        tif_files=dgm_tile_paths(UMRING),
        source_epsg=SOURCE_EPSG,
        vertical_epsg=DGM_TILE_VERTICAL_EPSG,
        basepoint_psets=extract_psets_basepoint(containers) or None,
    )
    app = TreesRustApp if rust else TreesGenericApp
    return app.build_ifc(records, **common)


def run_terrain(containers: List[Container], output: Path, rust: bool, typ2: bool) -> Optional[Path]:
    guide_records = (
        records_from_geojson_feature_collection(_load_json(NUTZUNG_FILE), nutzarten=GUIDE_NUTZARTEN) if typ2 else None
    )
    app = TerrainRustApp if rust else TerrainGenericApp
    return app.from_geotiffs(
        tif_files=dgm_tile_paths(UMRING),
        request_params=_request(containers, DGM_TILE_VERTICAL_EPSG),
        output_path=output,
        guide_records=guide_records,
    )


def run_city(containers: List[Container], output: Path, rust: bool) -> Optional[Path]:
    gml_files = [str(PathConfig.ASSETS / name) for name in CITY_TILES]
    request = _request(containers, DGM_TILE_VERTICAL_EPSG)
    if rust:
        return CityRustApp.from_gml_files(gml_files=gml_files, request_params=request, mode="mesh", output_path=output)
    return CityGenericApp.from_gml_files(gml_files=gml_files, request_params=request, output_path=output)


def run_flurstuecke(containers: List[Container], output: Path) -> Optional[Path]:
    records = load_flurstuecke_records(DATA_DIR / FLURSTUECKE_FILE)
    logger.info("  %d Flurstueck(e)", len(records))
    return FlurstueckeGenericApp.build_ifc(records, request_params=_request(containers), output_path=output)


def run_boreholes(containers: List[Container], output: Path) -> Optional[Path]:
    records = BoreholeMLProcessor().parse(gzip.decompress((DATA_DIR / BOREHOLES_FILE).read_bytes()))
    logger.info("  %d borehole(s)", len(records))
    return BoreholesGenericApp.build_ifc(
        records, request_params=_request(containers, BOREHOLES_VERTICAL_EPSG), output_path=output
    )


_TREES = ("Umgebung", "Gehoelz", "Umgebung")
_TERRAIN = ("Umgebung", "Gelaende", "Umgebung")
_CITY = ("Umgebung", "Bauwerkskubatur", "Umgebung")

WORKFLOWS = [
    Workflow("nullpunkt_generic", *_TERRAIN, partial(run_nullpunkt, rust=False)),
    Workflow("nullpunkt_rust", *_TERRAIN, partial(run_nullpunkt, rust=True)),
    Workflow("001_baumkataster_generic", *_TREES, partial(run_trees, rust=False)),
    Workflow("001_baumkataster_rust", *_TREES, partial(run_trees, rust=True)),
    Workflow("002_gelaendemodell_typ1_generic", *_TERRAIN, partial(run_terrain, rust=False, typ2=False)),
    Workflow("002_gelaendemodell_typ1_rust", *_TERRAIN, partial(run_terrain, rust=True, typ2=False)),
    Workflow("002_gelaendemodell_typ2_generic", *_TERRAIN, partial(run_terrain, rust=False, typ2=True)),
    Workflow("002_gelaendemodell_typ2_rust", *_TERRAIN, partial(run_terrain, rust=True, typ2=True)),
    Workflow("003_stadtmodell_generic", *_CITY, partial(run_city, rust=False)),
    Workflow("003_stadtmodell_rust", *_CITY, partial(run_city, rust=True)),
    Workflow("004_flurstuecke_generic", "Umgebung", "Flurstueck", "Umgebung", run_flurstuecke),
    Workflow("005_bohrungen_generic", "GeotechnikBaugrund", "Baugrundaufschluss", "GeotechnikBaugrund", run_boreholes),
]


def expected_nullpunkt_psets(workflow: Workflow) -> Dict[str, Dict[str, str]]:
    return {
        "Pset_Georeferenzierung": {"_Hoehensystem": "DHHN2016", "_Lagestatus": "LS310"},
        "Pset_Objektinformation": {},
        "Pset_Modellinformation": {
            "_ArtFachmodell": workflow.art_fachmodell,
            "_ArtTeilmodell": workflow.art_teilmodell,
            "_Ersteller": ERSTELLER,
            "_GemObjektkatalog": workflow.gem_objektkatalog,
        },
        "Pset_Hyperlink": {"_Hyperlink_001": HYPERLINK, "_Hyperlink_001_Bemerkung": HYPERLINK_BEMERKUNG},
    }


def check_nullpunkt(workflow: Workflow, ifc_path: Path) -> List[str]:
    """Log the Nullpunktobjekt psets and return the deviations from the request."""
    model = ifcopenshell.open(str(ifc_path))
    nullpunkte = [e for e in model.by_type("IfcBuildingElementProxy") if e.Name == "Nullpunktobjekt"]
    if len(nullpunkte) != 1:
        return [f"{len(nullpunkte)} Nullpunktobjekt(e) instead of 1"]

    nullpunkt = nullpunkte[0]
    psets = ifcopenshell.util.element.get_psets(nullpunkt)
    layers = [layer.Name for layer in ifcopenshell.util.element.get_layers(model, nullpunkt)]
    logger.info("  Nullpunktobjekt #%d, layer(s): %s", nullpunkt.id(), layers or "-")
    for pset_name, props in sorted(psets.items()):
        values = {k: v for k, v in props.items() if k != "id"}
        logger.info("    %s: %s", pset_name, values)

    deviations = []
    for pset_name, props in expected_nullpunkt_psets(workflow).items():
        if pset_name not in psets:
            deviations.append(f"{pset_name} missing")
            continue
        for prop, value in props.items():
            actual = psets[pset_name].get(prop)
            if actual != value:
                deviations.append(f"{pset_name}.{prop} = {actual!r}, expected {value!r}")
    return deviations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the portal workflows and check the Nullpunktobjekt.")
    parser.add_argument(
        "workflows",
        nargs="*",
        metavar="WORKFLOW",
        help="Run only workflows whose key contains one of these texts, e.g. '003' or 'rust' "
        "or '002_gelaendemodell_typ2_generic'. Default: all.",
    )
    parser.add_argument("--list", action="store_true", help="List the workflow keys and exit.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.list:
        for workflow in WORKFLOWS:
            print(workflow.key)
        return
    selected = [w for w in WORKFLOWS if not args.workflows or any(text in w.key for text in args.workflows)]
    if not selected:
        sys.exit(f"No workflow matches {args.workflows}; see --list")

    results: Dict[str, List[str]] = {}
    for workflow in selected:
        logger.info("=== %s ===", workflow.key)
        start = time.perf_counter()
        ifc_path = workflow.run(form_containers(workflow), workflow.output)
        if not ifc_path:
            results[workflow.key] = ["IFC build failed"]
            continue
        logger.info("  %s (%.1f s)", Path(ifc_path).name, time.perf_counter() - start)
        results[workflow.key] = check_nullpunkt(workflow, Path(ifc_path))

    logger.info("=== Nullpunktobjekt summary ===")
    for key, deviations in results.items():
        if not deviations:
            logger.info("OK          %s", key, extra={"debug_category": "success"})
            continue
        logger.warning("ABWEICHUNG  %s", key)
        for deviation in deviations:
            logger.warning("              - %s", deviation)

    if any(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    setup_logging()
    main()
