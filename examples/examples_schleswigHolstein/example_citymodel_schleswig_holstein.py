"""
Schleswig-Holstein city model example — LoD1 and LoD2.

ADV-style tiles under ``examples/assets/data_schleswigHolstein``.
EPSG:25832 (ETRS89 / UTM zone 32N), tile ``32_573_6021_1_SH``.
Uses ``export_citygml_tile_to_ifc`` (Hamburg defaults for hyperlink and layer).

Place the downloaded CityGML files next to each other, for example::

    LoD1_32_573_6021_1_SH.xml
    LoD2_32_573_6021_1_SH.xml

Outputs under ``PathConfig.OUTPUT``. With a building filter, the stem includes
that id (for example ``..._lod1_DESHPDHK0001uU4a.ifc``).
"""

import time
from pathlib import Path

from BIMFabrikHH_core.apps.city.app import export_citygml_tile_to_ifc
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

logger = get_logger()

# ---------------------------------------------------------------------------
# Export controls — edit these before running
# ---------------------------------------------------------------------------
EXPORT_LOD: str = "both"
# None = full tile. Use one building id for a quick test run.
FILTER_BUILDING_ID: str | None = None  # e.g. "DESHPDHK0001uU4a"
# ---------------------------------------------------------------------------

SH_DATA = PathConfig.ASSETS / "data_schleswigHolstein"

LOD_CONFIG = {
    "lod1": {
        "gml": SH_DATA / "LoD1_32_573_6021_1_SH.xml",
        "output": PathConfig.OUTPUT / "output_citymodel_schleswig_holstein_lod1.ifc",
        "project_name": "SchleswigHolstein_CityModel_LoD1",
        "color": (1.0, 1.0, 0.498),
    },
    "lod2": {
        "gml": SH_DATA / "LoD2_32_573_6021_1_SH.xml",
        "output": PathConfig.OUTPUT / "output_citymodel_schleswig_holstein_lod2.ifc",
        "project_name": "SchleswigHolstein_CityModel_LoD2",
        "color": (1.0, 0.8, 0.4),
    },
}


def build_ifc_for_lod(lod_name: str, cfg: dict, building_id: str | None = None) -> tuple[bool, Path]:
    gml_path = cfg["gml"]
    output_path: Path = cfg["output"]
    resolved_out = output_path.with_stem(output_path.stem + f"_{building_id}") if building_id else output_path

    logger.info(f"[{lod_name.upper()}] Parsing {gml_path.name} ...")

    result = export_citygml_tile_to_ifc(
        gml_path,
        output_path,
        building_id_filter=building_id,
        append_building_id_to_output_stem=building_id is not None,
        project_name=cfg["project_name"],
        site_name="SchleswigHolstein_Site",
        building_container_name=f"SchleswigHolstein_{lod_name.upper()}",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
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
