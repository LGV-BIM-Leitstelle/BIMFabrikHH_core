"""Column-name schema for tree DataFrames.

:class:`TreeColumnSchema` maps the logical tree attributes that
:func:`BIMFabrikHH_core.apps.trees.processing.dataframe_to_records`
reads to actual DataFrame column names. It replaces the ad-hoc
15-``col_*``-kwargs interface that ``dataframe_to_records`` used to
expose.

Two presets are shipped:

- :data:`DEFAULT_OAF_SCHEMA` — Hamburg OGC API Features / surveying
  convention (the current defaults).
- :data:`BAUMKATASTER_SCHEMA` — Strassenbaumkataster convention.

For one-off overrides, use :func:`dataclasses.replace`::

    from BIMFabrikHH_core.apps.trees import DEFAULT_OAF_SCHEMA
    from dataclasses import replace

    schema = replace(DEFAULT_OAF_SCHEMA, baumhoehe="hohe")
    dataframe_to_records(df, aufnahmedatum="2026-04-01", schema=schema)
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TreeColumnSchema:
    """DataFrame column-name map for :func:`dataframe_to_records`.

    Every field is the **name of a column in the input DataFrame**.
    None of these are IFC property names or default values — those live
    in the Pydantic pset models and in ``dataframe_to_records`` kwargs
    respectively.
    """

    # Position (project CRS).
    easting: str = "Easting"
    northing: str = "Northing"
    elevation: str = "Elevation"

    # Identification / taxonomy.
    baumnummer: str = "baumnummer"
    gattung: str = "gattung_deutsch"
    art: str = "art_deutsch"
    pflanzjahr_primary: str = "pflanzjahr_portal"
    pflanzjahr_fallback: str = "pflanzjahr"

    # Dimensions. ``stammumfang_cm`` is trunk circumference in cm (Hamburg
    # OGC convention); ``dataframe_to_records`` converts it to a diameter
    # in meters internally.
    kronendurchmesser: str = "kronendurchmesser"
    stammumfang_cm: str = "stammumfang"
    baumhoehe: str = "baumhoehe"

    # Location metadata.
    strasse: str = "strasse"
    stadtteil: str = "stadtteil"
    bezirk: str = "bezirk"


DEFAULT_OAF_SCHEMA: TreeColumnSchema = TreeColumnSchema()
"""Hamburg OGC API Features / surveying convention."""


BAUMKATASTER_SCHEMA: TreeColumnSchema = replace(
    DEFAULT_OAF_SCHEMA,
    pflanzjahr_primary="pflanzjahr",
    pflanzjahr_fallback="pflanzjahr",
)
"""Strassenbaumkataster HH convention.

Differs from :data:`DEFAULT_OAF_SCHEMA` only in the ``pflanzjahr`` columns:
the Strassenbaumkataster dataset has a single ``pflanzjahr`` column and
no ``pflanzjahr_portal`` fallback.
"""


__all__ = [
    "BAUMKATASTER_SCHEMA",
    "DEFAULT_OAF_SCHEMA",
    "TreeColumnSchema",
]
