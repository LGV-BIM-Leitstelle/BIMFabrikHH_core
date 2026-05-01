"""
Sachsen city model example — LoD1 and LoD2.

Parses the CityGML tiles from examples/assets/data_sachsen and writes two
separate IFC files, one per LoD. Uses EPSG:25833 (UTM zone 33N, Sachsen).
Uses :class:`CityBasicApp` (Hamburg pipeline: includes Pset_Hyperlink).

Outputs under ``PathConfig.OUTPUT``; with a building filter the stem includes
that id.
"""

import time
from pathlib import Path
from typing import Optional

from BIMFabrikHH_core.apps.city import CityBasicApp
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

logger = get_logger()

EXPORT_LOD: str = "both"  # "lod1" | "lod2" | "both"
FILTER_BUILDING_ID: Optional[str] = None  # "DESNATPU1000C1qE"  # e.g. "DESNATPU1000C1qE"

SACHSEN_DATA = PathConfig.ASSETS / "data_sachsen"

LOD_CONFIG = {
    "lod1": {
        "gml": SACHSEN_DATA / "lod1_33410_5652_2_sn_citygml" / "lod1_33410_5652_2_sn.gml",
        "output": PathConfig.OUTPUT / "output_citymodel_sachsen_lod1.ifc",
        "project_name": "Sachsen_CityModel_LoD1",
        "color": (1.0, 1.0, 0.498),
    },
    "lod2": {
        "gml": SACHSEN_DATA / "lod2_33410_5652_2_sn_citygml" / "lod2_33410_5652_2_sn.gml",
        "output": PathConfig.OUTPUT / "output_citymodel_sachsen_lod2.ifc",
        "project_name": "Sachsen_CityModel_LoD2",
        "color": (1.0, 0.8, 0.4),
    },
}


def _build_project_container(project_name: str, site_name: str, building_name: str) -> Container:
    """Wrap project/site/building names in the ``Projektinformationen`` container."""
    return Container(
        containerTitle="Projektinformationen",
        containerId="Projektinformationen",
        components={
            "projectname": Component(title="Projektname", value=project_name),
            "sitename": Component(title="IfcSite", value=site_name),
            "buildingname": Component(title="IfcBuilding", value=building_name),
        },
    )


def build_ifc_for_lod(lod_name: str, cfg: dict, building_id: Optional[str] = None) -> tuple[bool, Path]:
    """Parse one CityGML file and write IFC via :class:`CityBasicApp`."""
    gml_path: Path = cfg["gml"]
    output_path: Path = cfg["output"]
    resolved_out = output_path.with_stem(output_path.stem + f"_{building_id}") if building_id else output_path

    logger.info(f"[{lod_name.upper()}] Parsing {gml_path.name} ...")

    request_params = RequestParams(
        bbox=None,
        containers=[
            _build_project_container(
                project_name=cfg["project_name"],
                site_name="Sachsen_Site",
                building_name=f"Sachsen_{lod_name.upper()}",
            )
        ],
    )

    result = CityBasicApp.from_gml_files(
        gml_files=[gml_path],
        request_params=request_params,
        building_id_filter=building_id,
        output_path=resolved_out,
        coordinate_system=CoordinateSystemTemplates.epsg_25833(),
        representation_color=cfg["color"],
    )

    if result is None:
        msg = f"Building ID '{building_id}' not found" if building_id else "No buildings found"
        logger.error(f"[{lod_name.upper()}] {msg} — skipping.")
        return False, resolved_out

    logger.info(f"[{lod_name.upper()}] Saved to {result}", extra={"debug_category": "success"})
    return True, result


def main():
    total_start = time.perf_counter()
    lods = list(LOD_CONFIG.keys()) if EXPORT_LOD == "both" else [EXPORT_LOD]

    for lod_name in lods:
        cfg = LOD_CONFIG[lod_name]
        t = time.perf_counter()
        ok, out_path = build_ifc_for_lod(lod_name, cfg, building_id=FILTER_BUILDING_ID)
        elapsed = time.perf_counter() - t
        status = "OK" if ok else "FAIL"
        print(f"{status} {lod_name.upper()}: {elapsed:.2f}s  ->  {out_path}")

    print(f"\nTotal: {time.perf_counter() - total_start:.2f}s")


if __name__ == "__main__":
    main()
