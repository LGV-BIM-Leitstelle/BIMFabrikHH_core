"""
Example: basic trees IFC (``TreesBasicApp`` pipeline)
=====================================================

Flow:

1. Hand-authored sample tree attributes → ``pd.DataFrame``.
2. Optional DGM elevation enrichment from a local GeoTIFF.
3. ``dataframe_to_records(df)`` → ``list[TreeRecord]`` (with
   Pydantic psets attached).
4. ``TreesBasicApp.build_ifc(records, ...)`` builds the IFC model
   (mesh trunk + icosphere crown via ``ifcopenshell.api``) and a
   basepoint quad at the WGS84 bbox min corner (converted to EPSG:25832).
"""

from __future__ import annotations

import pandas as pd

from BIMFabrikHH_core import BoundingBoxParams, TreesBasicApp
from BIMFabrikHH_core.apps.trees import DEFAULT_OAF_SCHEMA, dataframe_to_records
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.georeferencing.crs_transform import bbox_wgs84_to_epsg25832
from BIMFabrikHH_core.core.georeferencing.extract_elevation import (
    extract_elevation_df_from_geotiff,
)

logger = get_logger()


def main() -> None:
    """Process tree data to create IFC."""

    bbox_wgs84 = BoundingBoxParams(min_x=9.877815, min_y=53.492363, max_x=9.887343, max_y=53.496003)

    schema = DEFAULT_OAF_SCHEMA
    sample_data = [
        {
            schema.easting: 558406.01,
            schema.northing: 5927514.51,
            schema.kronendurchmesser: 18.0,
            schema.stammumfang_cm: 120.0,
            schema.baumnummer: "Demo-1",
            schema.gattung: "Ahorn",
            schema.art: "Spitz-Ahorn",
            schema.strasse: "Musterweg",
            schema.stadtteil: "Demo-Stadtteil",
            schema.bezirk: "Demo-Bezirk",
            schema.pflanzjahr_fallback: 1990,
        },
        {
            schema.easting: 558553.52,
            schema.northing: 5927499.96,
            schema.kronendurchmesser: 26.0,
            schema.stammumfang_cm: 200.0,
            schema.baumnummer: "Demo-2",
            schema.gattung: "Linde",
            schema.art: "Winter-Linde",
            schema.strasse: "Musterweg",
            schema.stadtteil: "Demo-Stadtteil",
            schema.bezirk: "Demo-Bezirk",
            schema.pflanzjahr_fallback: 1985,
        },
    ]

    df = pd.DataFrame(sample_data)

    tif_path = str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")
    try:
        df = extract_elevation_df_from_geotiff(df, tif_path, schema.easting, schema.northing, schema.elevation)
    except Exception as e:
        logger.warning(f"DGM elevation extraction skipped: {e}")

    records = dataframe_to_records(
        df,
        aufnahmedatum="undefiniert",
        schema=schema,
        source_name="example_basic_trees",
        name_prefix="Demo_",
    )

    bp_x, bp_y, *_ = bbox_wgs84_to_epsg25832((bbox_wgs84.min_x, bbox_wgs84.min_y, bbox_wgs84.max_x, bbox_wgs84.max_y))

    ifc_path = TreesBasicApp.build_ifc(
        records,
        basepoint_origin=(bp_x, bp_y),
        basepoint_size=1.0,
    )

    if ifc_path:
        logger.info(
            f"[OK] Successfully created {ifc_path.name}",
            extra={"debug_category": "success"},
        )
        logger.info(
            f"Path: {ifc_path.parent}",
            extra={"debug_category": "success"},
        )
    else:
        logger.error("[FAIL] Failed to create tree IFC model")


if __name__ == "__main__":
    setup_logging()
    main()
