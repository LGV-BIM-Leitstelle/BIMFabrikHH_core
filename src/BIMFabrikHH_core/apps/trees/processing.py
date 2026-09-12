"""Shared tree data-processing helpers.

This module encapsulates everything that happens between a tabular input
(dict rows or DataFrame) and the ``list[TreeRecord]`` consumed by the
record-builder apps (``TreesBasicApp`` / ``TreesGenericApp``).

Stages covered here:

1. :func:`calculate_tree_height` — height fallback (measured vs. crown-based
   rule of thumb, clamped to a minimum).
2. :func:`build_tree_psets` — factory for the Pydantic pset templates
   (``Pset_Objektinformation_Tree`` + ``Pset_Bauwerk_Tree``).
3. :func:`dataframe_to_records` — turn a DataFrame of tree attributes into
   ``list[TreeRecord]`` with psets attached.
4. :func:`validate_tree_records` — pre-flight domain sanity check on the
   records before IFC generation.
5. :func:`resolve_tree_dimensions` and :func:`collect_pydantic_psets` —
   pure per-record helpers consumed by ``TreesBasicApp`` and
   ``TreesGenericApp`` so their IFC-writing code is truly column- and
   data-agnostic.
6. :func:`tree_crown_detail_from_containers` — OGC containers → crown
   ``detail`` (uses :func:`~BIMFabrikHH_core.core.ogc_extractor.extract_level_of_geometry`).
7. :func:`drape_records_on_dgm` — set each record's Z from DGM GeoTIFF tiles
   (no terrain IFC / mesh required).

Pydantic handles type / required-field validation on :class:`TreeRecord`
itself, so this module only layers on the domain knowledge (circumference
→ diameter conversion, sensible ranges, unit-carrying ``Quantity`` values).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

import numpy as np
import pandas as pd
from ifcfactory import ureg
from pydantic import BaseModel

from BIMFabrikHH_core.core.georeferencing import sample_elevations_for_points
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_level_of_geometry
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree
from BIMFabrikHH_core.data_models.tree_record import TreeRecord

from .column_schema import DEFAULT_OAF_SCHEMA, TreeColumnSchema

logger = logging.getLogger(__name__)

MIN_TREE_HEIGHT_M: float = 1.10
CROWN_TO_HEIGHT_RATIO: float = 0.85
MIN_STAMMDURCHMESSER_M: float = 0.05
MIN_TRUNK_RADIUS_M: float = 0.025
DEFAULT_KRONENDURCHMESSER_M: float = 5.0
DEFAULT_STAMMUMFANG_CM: float = 100.0
DEFAULT_DETAIL: int = 1
DEFAULT_SEGMENTS: int = 8
_MAX_TREE_CROWN_DETAIL: int = 4

# ``_LoG`` / ``_LoI`` are owned by Pset_Objektinformation_Tree; mirrored here so
# the helper signatures below cannot drift away from the model.
DEFAULT_TREE_LOG: int = Pset_Objektinformation_Tree.model_fields["log"].default
DEFAULT_TREE_LOI: int = Pset_Objektinformation_Tree.model_fields["loi"].default

# Trunk-height fallback constants (used when ``baumhoehe`` is not set).
_MIN_TRUNK_HEIGHT_M: float = 3.5
_TRUNK_HEIGHT_CROWN_FACTOR: float = 1.35
_SMALL_CROWN_DIAMETER_M: float = 3.0


@dataclass(frozen=True)
class TreeDimensions:
    """Visual dimensions of one tree, derived from a :class:`TreeRecord`.

    All values are in metres. Used by both ``TreesBasicApp`` and
    ``TreesGenericApp`` so the trunk-height / radius rules live in one
    place.
    """

    crown_radius: float
    trunk_radius: float
    trunk_height: float


def resolve_tree_dimensions(
    record: TreeRecord,
    *,
    min_crown_radius_m: float = 0.0,
    min_trunk_radius_m: float = MIN_TRUNK_RADIUS_M,
) -> TreeDimensions:
    """Compute ``TreeDimensions`` for a :class:`TreeRecord`.

    Rule (same one both tree apps previously duplicated):

    * ``crown_radius`` = ``kronendurchmesser / 2``, floored at
      ``min_crown_radius_m``.
    * ``trunk_radius`` = ``stammdurchmesser / 2``, floored at
      ``min_trunk_radius_m`` (default 5 cm diameter).
    * ``trunk_height`` is taken from ``record.baumhoehe`` when available
      (with the crown radius added so the crown sits above the trunk);
      otherwise it falls back to ``1.35 × crown_diameter`` for crowns
      at least 3 m across and to a minimum of 3.5 m for smaller crowns.

    ``record.baumhoehe`` is therefore the **Stammhöhe**, not the whole tree.
    The crown sphere is centred on the trunk top, so the treetop ends up one
    full ``kronendurchmesser`` higher — see :func:`full_tree_height`, which is
    what belongs in the ``_Baumhoehe`` property.

    Args:
        record: The tree record.
        min_crown_radius_m: Lower bound on ``crown_radius``. ``TreesBasicApp``
            passes ``1.0`` to keep small crowns visible at LOD 1; the
            generic app uses ``0.0``.
        min_trunk_radius_m: Lower bound on ``trunk_radius``. Avoids
            degenerate cylinders for newly planted trees.

    Returns:
        Frozen :class:`TreeDimensions`.
    """
    crown_radius = max(min_crown_radius_m, record.kronendurchmesser / 2)
    trunk_radius = max(min_trunk_radius_m, record.stammdurchmesser / 2)
    crown_diameter = crown_radius * 2

    if record.baumhoehe is not None and record.baumhoehe > 0:
        trunk_height = float(record.baumhoehe) + crown_radius
    elif crown_diameter < _SMALL_CROWN_DIAMETER_M:
        trunk_height = _MIN_TRUNK_HEIGHT_M
    else:
        trunk_height = _TRUNK_HEIGHT_CROWN_FACTOR * crown_diameter

    return TreeDimensions(
        crown_radius=crown_radius,
        trunk_radius=trunk_radius,
        trunk_height=trunk_height,
    )


def tree_crown_detail_from_containers(containers: Any) -> int:
    """``TreeRecord.detail`` (crown mesh / icosphere level) from OGC containers.

    Uses :func:`BIMFabrikHH_core.core.ogc_extractor.extract_level_of_geometry`
    then clamps to ``[1, _MAX_TREE_CROWN_DETAIL]`` so values fit
    :class:`TreeRecord` and ``TreesGenericApp`` / ``TreesBasicApp``.

    Args:
        containers: Same shape as API request ``containers`` (optional list).

    Returns:
        Integer in ``1`` … ``4`` suitable for :func:`dataframe_to_records`
        ``detail=`` and ``TreesBasicApp.build_ifc`` ``level_of_geom``.
    """
    lod = extract_level_of_geometry(containers or [])
    return max(1, min(_MAX_TREE_CROWN_DETAIL, int(lod)))


def tree_log_from_containers(containers: Any) -> int:
    """``_LoG`` (100-scale) from the OGC request's ``level_of_geom``.

    The request speaks LoD ``1`` … ``4`` while the property set publishes
    ``100`` … ``400``, so the requested level is scaled by 100. A request
    without a level container yields :data:`DEFAULT_TREE_LOG` rather than 100,
    which is why the extractor is given an explicit ``default``.

    Args:
        containers: Same shape as API request ``containers`` (optional list).

    Returns:
        Integer in ``100`` … ``400`` suitable for :func:`build_tree_psets`
        and :func:`dataframe_to_records` ``log=``.
    """
    lod = extract_level_of_geometry(containers or [], default=DEFAULT_TREE_LOG // 100)
    return max(100, min(_MAX_TREE_CROWN_DETAIL * 100, int(lod) * 100))


def collect_pydantic_psets(
    record: TreeRecord,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Extract the Pydantic pset templates stored on a :class:`TreeRecord`.

    Returns an empty list when ``include_property_sets`` is ``False`` or
    when ``record.psets`` is empty. Non-``BaseModel`` entries are logged
    as warnings and skipped (matches the previous behaviour of both
    tree apps).
    """
    if not include_property_sets or not record.psets:
        return []

    out: List[BaseModel] = []
    for pset_name, value in record.psets.items():
        if isinstance(value, BaseModel):
            out.append(value)
        else:
            logger.warning(
                "Tree %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                record.name,
                pset_name,
                type(value).__name__,
            )
    return out


def calculate_tree_height(
    kronendurchmesser: float,
    baumhoehe: Optional[float] = None,
) -> tuple[float, str]:
    """Resolve a tree height value + a German remark describing the rule used.

    Policy (same as cadaster / surveying apps):

    - If ``baumhoehe`` is present and positive, use it — clamped to
      :data:`MIN_TREE_HEIGHT_M`.
    - Otherwise, derive the height from the crown diameter as
      :data:`CROWN_TO_HEIGHT_RATIO` × ``kronendurchmesser`` — clamped to
      :data:`MIN_TREE_HEIGHT_M`.

    Args:
        kronendurchmesser: Crown diameter in meters. Used as the fallback
            source when ``baumhoehe`` is not available.
        baumhoehe: Measured tree height in meters, or ``None``.

    Returns:
        ``(height_m, remark)`` where ``height_m`` is always
        ``>= MIN_TREE_HEIGHT_M``.
    """
    if baumhoehe is not None and baumhoehe > 0:
        measured = float(baumhoehe)
        final = max(measured, MIN_TREE_HEIGHT_M)
        if final > measured:
            return (
                final,
                f"Gemessene Baumhoehe ({measured:.2f}m) auf Mindesthöhe " f"{MIN_TREE_HEIGHT_M:.2f}m angepasst",
            )
        return final, "Gemessene Baumhoehe"

    calculated = CROWN_TO_HEIGHT_RATIO * float(kronendurchmesser)
    final = max(calculated, MIN_TREE_HEIGHT_M)
    if final > calculated:
        return (
            final,
            f"{CROWN_TO_HEIGHT_RATIO} × {float(kronendurchmesser):.2f}m Kronendurchmesser "
            f"= {calculated:.2f}m, auf Mindesthöhe {MIN_TREE_HEIGHT_M:.2f}m angepasst",
        )
    return (
        final,
        f"{CROWN_TO_HEIGHT_RATIO} × {float(kronendurchmesser):.2f}m Kronendurchmesser " f"= {calculated:.2f}m",
    )


def full_tree_height(
    stammhoehe_m: float,
    kronendurchmesser_m: float,
) -> tuple[float, str]:
    """Gesamthöhe + remark for ``_Baumhoehe``, from the trunk height.

    :func:`resolve_tree_dimensions` raises the trunk to
    ``stammhoehe_m + crown_radius`` and centres the crown sphere on that top,
    so the highest point of the tree sits one full ``kronendurchmesser`` above
    ``stammhoehe_m``. Publishing that sum keeps the property set in step with
    the geometry instead of reporting the bare trunk.

    Both inputs are rounded to centimetres before they are added, so the
    published value and the sum spelled out in the remark always agree.

    Not for stumps: ``is_stump`` records are written without a crown, so their
    trunk height already is the full height.

    Args:
        stammhoehe_m: Trunk height in metres, as returned by
            :func:`calculate_tree_height` and stored on ``TreeRecord.baumhoehe``.
        kronendurchmesser_m: Crown diameter in metres.

    Returns:
        ``(gesamthoehe_m, remark)`` ready for :func:`build_tree_psets`, with
        ``gesamthoehe_m`` rounded to two decimals.
    """
    stammhoehe = round(float(stammhoehe_m), 2)
    kronendurchmesser = round(float(kronendurchmesser_m), 2)
    gesamthoehe_m = round(stammhoehe + kronendurchmesser, 2)
    remark = (
        f"Gesamthöhe = {stammhoehe:.2f}m Stammhöhe "
        f"+ {kronendurchmesser:.2f}m Kronendurchmesser = {gesamthoehe_m:.2f}m"
    )
    return gesamthoehe_m, remark


def build_tree_psets(
    *,
    baumnummer: str,
    gattung: str,
    art: str,
    pflanzjahr: int,
    kronendurchmesser_m: float,
    stammdurchmesser_m: Optional[float],
    baumhoehe_m: float,
    baumhoehe_bemerkung: str,
    aufnahmedatum: str,
    stadtteil: str = "undefiniert",
    bezirk: str = "undefiniert",
    bemerkung: str = "undefiniert",
    status_vegetation: str = "undefiniert",
    strasse: str = "undefiniert",
    log: int = DEFAULT_TREE_LOG,
    loi: int = DEFAULT_TREE_LOI,
) -> Dict[str, BaseModel]:
    """Build the Pydantic pset templates for a single tree.

    Returns ``{m.pset_name: m}`` so the ``IFC`` pset keys follow the model's
    ``pset_name`` ClassVar (``"Pset_Objektinformation"`` and ``"Pset_Bauwerk"``).

    This helper intentionally takes **no** row dict and does **no** height
    calculation — callers compute ``baumhoehe_m`` / ``baumhoehe_bemerkung``
    upstream via :func:`calculate_tree_height` and pass them in. Keeps the
    function a pure template factory.

    Args:
        baumnummer: Tree number (free text).
        gattung: German genus name (``_Gattung``).
        art: German species name for ``_ArtBaum``.
        pflanzjahr: Year of planting (integer).
        kronendurchmesser_m: Crown diameter in meters.
        stammdurchmesser_m: Trunk diameter in meters, or ``None`` if unknown.
        baumhoehe_m: Tree height in meters, already resolved.
        baumhoehe_bemerkung: Remark describing how the height was derived.
        aufnahmedatum: Survey date as ISO string (``"YYYY-MM-DD"``).
        stadtteil: District.
        bezirk: Borough.
        bemerkung: Free-text remark / source label (e.g. the data source name).
        status_vegetation: Status flag (e.g. ``"Bestand"``).
        strasse: Street name for ``Pset_Bauwerk._Strassenname``.
        log: Level of Geometry written to ``_LoG``.
        loi: Level of Information written to ``_LoI``.

    Returns:
        ``{pset_name: pydantic_model}`` suitable for ``TreeRecord.psets``.
    """
    objekt = Pset_Objektinformation_Tree(
        baumnummer=baumnummer,
        gattung_deutsch=gattung,
        art_baum=art,
        pflanzjahr=int(pflanzjahr),
        kronendurchmesser=ureg.Quantity(float(kronendurchmesser_m), "meter"),
        stammdurchmesser=(
            ureg.Quantity(float(stammdurchmesser_m), "meter") if stammdurchmesser_m is not None else None
        ),
        baumhoehe=ureg.Quantity(float(baumhoehe_m), "meter"),
        baumhoehe_bemerkung=baumhoehe_bemerkung,
        aufnahmedatum_vermessung=aufnahmedatum,
        stadtteil=stadtteil,
        bezirk=bezirk,
        bemerkung=bemerkung,
        status_vegetation=status_vegetation,
        log=int(log),
        loi=int(loi),
    )
    bauwerk = Pset_Bauwerk_Tree(strassenname=strasse)
    return {m.pset_name: m for m in (objekt, bauwerk)}


def _stammumfang_cm_to_stammdurchmesser_m(
    stammumfang_cm: float,
    *,
    minimum_m: float = MIN_STAMMDURCHMESSER_M,
) -> float:
    """Convert trunk circumference (cm) to trunk diameter (m) with a floor.

    Diameter = circumference / π. Circumference input is in **centimeters**
    (Hamburg OGC API convention), output in **meters**.
    """
    diameter_m = (float(stammumfang_cm) / math.pi) / 100.0
    return max(minimum_m, diameter_m)


def dataframe_to_records(
    df: pd.DataFrame,
    *,
    aufnahmedatum: str,
    schema: TreeColumnSchema = DEFAULT_OAF_SCHEMA,
    source_name: str = "undefiniert",
    name_prefix: str = "",
    name_index_start: int = 0,
    detail: int = DEFAULT_DETAIL,
    segments: int = DEFAULT_SEGMENTS,
    default_kronendurchmesser_m: float = DEFAULT_KRONENDURCHMESSER_M,
    default_stammumfang_cm: float = DEFAULT_STAMMUMFANG_CM,
    status_vegetation: str = "undefiniert",
    log: int = DEFAULT_TREE_LOG,
    loi: int = DEFAULT_TREE_LOI,
) -> List[TreeRecord]:
    """Materialize a list of :class:`TreeRecord` from a tree DataFrame.

    Handles the usual pre-processing previously duplicated in cadaster and
    core/basic: trunk-circumference → diameter conversion, pflanzjahr
    fallback chain, height fallback via :func:`calculate_tree_height`, and
    pset construction via :func:`build_tree_psets`.

    Args:
        df: DataFrame with one row per tree. Column names are resolved via
            ``schema``.
        aufnahmedatum: Survey date written to
            ``Pset_Objektinformation._AufnahmedatumVermessung`` (ISO string).
        schema: Column-name mapping. Defaults to
            :data:`DEFAULT_OAF_SCHEMA` (Hamburg OGC API / surveying). Pass
            :data:`BAUMKATASTER_SCHEMA` for Strassenbaumkataster data, or
            build a custom one with ``dataclasses.replace``.
        source_name: Free-text label for the summary log line
            (e.g. ``"Strassenbaumkataster_HH"``).
        name_prefix: Prepended to the generated IFC name (``TreeRecord.name``).
        name_index_start: First index for name generation.
        detail: ``TreeRecord.detail`` value (crown geometry LOD).
        segments: ``TreeRecord.segments`` value (trunk polygon segments).
        default_kronendurchmesser_m: Fallback when the column is missing /
            NaN.
        default_stammumfang_cm: Fallback circumference (cm) when the column
            is missing / NaN.
        status_vegetation: Value for ``_StatusVegetation``.

    Returns:
        ``list[TreeRecord]`` in the same order as ``df`` rows.
    """
    if df.empty:
        return []

    records: List[TreeRecord] = []
    for idx, (_row_idx, row) in enumerate(df.iterrows()):
        row_dict = row.to_dict()

        def _num(key: str, default: float) -> float:
            val = row_dict.get(key)
            if val is None or pd.isna(val):
                return float(default)
            try:
                return float(val)
            except (TypeError, ValueError):
                return float(default)

        def _str(key: str, default: str = "undefiniert") -> str:
            val = row_dict.get(key)
            if val is None or (isinstance(val, float) and pd.isna(val)):
                return default
            return str(val)

        kronendurchmesser_m = _num(schema.kronendurchmesser, default_kronendurchmesser_m)
        stammumfang_cm = _num(schema.stammumfang_cm, default_stammumfang_cm)
        stammdurchmesser_m = _stammumfang_cm_to_stammdurchmesser_m(stammumfang_cm)

        baumhoehe_raw = row_dict.get(schema.baumhoehe)
        if baumhoehe_raw is None or (isinstance(baumhoehe_raw, float) and pd.isna(baumhoehe_raw)):
            baumhoehe_in: Optional[float] = None
        else:
            try:
                baumhoehe_in = float(baumhoehe_raw)
            except (TypeError, ValueError):
                baumhoehe_in = None

        height_m, _height_remark = calculate_tree_height(kronendurchmesser_m, baumhoehe_in)
        gesamthoehe_m, gesamthoehe_remark = full_tree_height(height_m, kronendurchmesser_m)

        pflanzjahr_val = row_dict.get(schema.pflanzjahr_primary)
        if pflanzjahr_val is None or (isinstance(pflanzjahr_val, float) and pd.isna(pflanzjahr_val)):
            pflanzjahr_val = row_dict.get(schema.pflanzjahr_fallback)
        try:
            pflanzjahr = int(float(pflanzjahr_val)) if pflanzjahr_val is not None else 9999
        except (TypeError, ValueError):
            pflanzjahr = 9999

        global_idx = name_index_start + idx
        baumnummer = _str(schema.baumnummer, default=f"{name_prefix}{global_idx + 1:03d}")

        easting = _num(schema.easting, 0.0)
        northing = _num(schema.northing, 0.0)
        elevation = _num(schema.elevation, 0.0)

        psets = build_tree_psets(
            baumnummer=baumnummer,
            gattung=_str(schema.gattung),
            art=_str(schema.art),
            pflanzjahr=pflanzjahr,
            kronendurchmesser_m=kronendurchmesser_m,
            stammdurchmesser_m=stammdurchmesser_m,
            baumhoehe_m=gesamthoehe_m,
            baumhoehe_bemerkung=gesamthoehe_remark,
            aufnahmedatum=aufnahmedatum,
            stadtteil=_str(schema.stadtteil),
            bezirk=_str(schema.bezirk),
            log=log,
            loi=loi,
            status_vegetation=status_vegetation,
            strasse=_str(schema.strasse),
        )

        records.append(
            TreeRecord(
                name=f"{name_prefix}Baum_{global_idx + 1:03d}",
                position=(easting, northing, elevation),
                kronendurchmesser=kronendurchmesser_m,
                stammdurchmesser=stammdurchmesser_m,
                detail=detail,
                segments=segments,
                baumhoehe=height_m,
                psets=psets,
            )
        )

    logger.info("Built %d TreeRecord(s) from DataFrame (source=%s)", len(records), source_name)
    return records


def drape_records_on_dgm(
    records: List[TreeRecord],
    tif_files: Iterable[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    default_elevation: float = 0.0,
) -> List[TreeRecord]:
    """Set each record's Z from DGM GeoTIFF tiles (EPSG:25832 XY unchanged).

    Samples every tile via :func:`sample_elevations_for_points`. Existing Z is
    overwritten so a leftover ``0`` cannot stick. Without tiles there is
    nothing to sample from and the records are returned unchanged.
    """
    tile_list = list(tif_files)
    if not records or not tile_list:
        return list(records)

    points_xy = np.array([(rec.position[0], rec.position[1]) for rec in records], dtype=float)
    elevations = sample_elevations_for_points(
        points_xy,
        tile_list,
        folder_path=folder_path,
        default_elevation=default_elevation,
    )
    draped: List[TreeRecord] = []
    for rec, z in zip(records, elevations):
        x, y, _ = rec.position
        draped.append(rec.model_copy(update={"position": (float(x), float(y), float(z))}))
    logger.info("Draped %d TreeRecord(s) onto DGM GeoTIFF(s)", len(draped))
    return draped


def validate_tree_records(
    records: Iterable[TreeRecord],
    *,
    max_kronendurchmesser_m: float = 100.0,
    max_stammdurchmesser_m: float = 5.0,
    max_baumhoehe_m: float = 150.0,
    min_segments: int = 3,
    max_detail: int = 4,
    max_errors_logged: int = 10,
) -> None:
    """Domain-range sanity check on a list of :class:`TreeRecord`.

    Pydantic already enforces field types and required keys at record
    construction time. This function layers on value-range checks that
    would otherwise surface as garbled IFC geometry:

    - ``position`` components must be finite.
    - ``kronendurchmesser`` in ``(0, max_kronendurchmesser_m]``.
    - ``stammdurchmesser`` in ``[0, max_stammdurchmesser_m]``.
    - ``baumhoehe`` (if set) in ``(0, max_baumhoehe_m]``.
    - ``detail`` in ``{1, ..., max_detail}``.
    - ``segments`` ``>= min_segments``.

    Args:
        records: Iterable of :class:`TreeRecord`.
        max_kronendurchmesser_m: Upper bound on crown diameter.
        max_stammdurchmesser_m: Upper bound on trunk diameter.
        max_baumhoehe_m: Upper bound on tree height.
        min_segments: Minimum polygon segments for the trunk cylinder.
        max_detail: Upper bound on the crown LOD integer.
        max_errors_logged: Maximum number of individual errors echoed in
            the log before truncating.

    Raises:
        ValueError: If any record fails validation; the exception message
            contains a summary of all errors.
    """
    errors: List[str] = []
    records_list = list(records)
    for idx, record in enumerate(records_list):
        label = record.name or f"Record_{idx}"

        x, y, z = record.position
        if any(math.isinf(v) or math.isnan(v) for v in (x, y, z)):
            errors.append(f"{label}: position has non-finite values {record.position}")

        if not (0.0 < record.kronendurchmesser <= max_kronendurchmesser_m):
            errors.append(
                f"{label}: kronendurchmesser out of range "
                f"(0, {max_kronendurchmesser_m}]: {record.kronendurchmesser}"
            )

        if record.stammdurchmesser < 0 or record.stammdurchmesser > max_stammdurchmesser_m:
            errors.append(
                f"{label}: stammdurchmesser out of range " f"[0, {max_stammdurchmesser_m}]: {record.stammdurchmesser}"
            )

        if record.baumhoehe is not None:
            if not (0.0 < float(record.baumhoehe) <= max_baumhoehe_m):
                errors.append(f"{label}: baumhoehe out of range " f"(0, {max_baumhoehe_m}]: {record.baumhoehe}")

        if not (1 <= record.detail <= max_detail):
            errors.append(f"{label}: detail out of range [1, {max_detail}]: {record.detail}")

        if record.segments < min_segments:
            errors.append(f"{label}: segments must be >= {min_segments}: {record.segments}")

    if errors:
        logger.error("Validation found %d error(s).", len(errors))
        for msg in errors[:max_errors_logged]:
            logger.error("  - %s", msg)
        if len(errors) > max_errors_logged:
            logger.error("  ... and %d more", len(errors) - max_errors_logged)
        raise ValueError(
            f"Tree record validation failed with {len(errors)} error(s). "
            f"First errors:\n  " + "\n  ".join(errors[:max_errors_logged])
        )

    logger.info("Validated %d TreeRecord(s) — all within domain ranges.", len(records_list))


__all__ = [
    "CROWN_TO_HEIGHT_RATIO",
    "DEFAULT_DETAIL",
    "DEFAULT_KRONENDURCHMESSER_M",
    "DEFAULT_OAF_SCHEMA",
    "DEFAULT_SEGMENTS",
    "DEFAULT_STAMMUMFANG_CM",
    "DEFAULT_TREE_LOG",
    "DEFAULT_TREE_LOI",
    "MIN_STAMMDURCHMESSER_M",
    "MIN_TREE_HEIGHT_M",
    "MIN_TRUNK_RADIUS_M",
    "TreeColumnSchema",
    "TreeDimensions",
    "build_tree_psets",
    "calculate_tree_height",
    "collect_pydantic_psets",
    "dataframe_to_records",
    "drape_records_on_dgm",
    "full_tree_height",
    "resolve_tree_dimensions",
    "tree_crown_detail_from_containers",
    "tree_log_from_containers",
    "validate_tree_records",
]
