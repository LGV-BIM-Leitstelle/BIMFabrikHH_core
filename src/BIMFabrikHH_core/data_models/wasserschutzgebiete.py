"""Hamburg Wasserschutzgebiete (OGC API Features) — input records.

Parsed from GeoJSON ``FeatureCollection`` responses such as
``/datasets/v1/wasserschutzgebiete/collections/wasserschutzgebiete/items``.
Geometry is expected as ``Polygon``; only the exterior ring is used.
Ring coordinates are either **EPSG:25832** ``(easting, northing)`` (default)
or **EPSG:4326** ``(lon, lat)`` — set ``geometry_crs`` when parsing.

Like :class:`TreeRecord`, each row carries IFC pset templates under
``psets`` (filled by :func:`records_from_geojson_feature_collection` or by
hand).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from BIMFabrikHH_core.core.ogc_extractor import (
    OgcGeometryCrs,
    ensure_feature_collection,
    feature_identifier,
    geojson_feature_properties,
    iter_geojson_features,
    parse_feature_polygon_exterior_ring,
)

GeometryCrs = OgcGeometryCrs

logger = logging.getLogger(__name__)


class WasserschutzgebietRecord(BaseModel):
    """One protection zone: geometry, flat API attributes, and optional psets (tree-style)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")
    exterior_ring: List[Tuple[float, float]] = Field(
        description="Exterior ring; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    geometry_crs: GeometryCrs = Field(
        default="EPSG:25832",
        description="CRS of ``exterior_ring`` vertex coordinates",
    )

    wsg: str = Field(description="Kürzel / Typ (z. B. WSG)")
    gebietsname: str = Field(description="Name des Schutzgebiets")
    rechtsgrundlage: str = Field(default="", description="Rechtsgrundlage / Verordnung")
    schutzzone: str = Field(default="", description="Schutzzone (z. B. Schutzzone II)")
    erfassungsgrundlage: str = Field(default="", description="Maßstab / Erfassungsgrundlage")
    info_kontakt: str = Field(default="", description="Link MetaVer / Kontakt")
    ausweisung: str = Field(default="", description="Ausweisungsdatum")
    bearbeitungsstand: str = Field(default="", description="Stand der Bearbeitung")
    info: str = Field(default="", description="Infoseite")
    idherkunft: int = Field(default=0, description="ID Herkunft (Quelle)")

    psets: Dict[str, BaseModel] = Field(default_factory=dict)


def collect_wasserschutz_psets(
    record: WasserschutzgebietRecord,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Extract Pydantic pset templates stored on :class:`WasserschutzgebietRecord` (cf. trees)."""
    if not include_property_sets or not record.psets:
        return []
    out: List[BaseModel] = []
    for pset_name, value in record.psets.items():
        if isinstance(value, BaseModel):
            out.append(value)
        else:
            logger.warning(
                "Wasserschutzgebiet %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                record.feature_id,
                pset_name,
                type(value).__name__,
            )
    return out


def _record_with_psets_from_payload(
    payload: dict[str, Any],
) -> WasserschutzgebietRecord:
    record = WasserschutzgebietRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_wasserschutzgebiete import (
        Pset_Objektinformation_Wasserschutzgebiet,
    )

    pset = Pset_Objektinformation_Wasserschutzgebiet(
        idebene3=record.schutzzone or "Wasserschutzgebiet",
        wsg=record.wsg,
        gebietsname=record.gebietsname,
        schutzzone=record.schutzzone,
        rechtsgrundlage=record.rechtsgrundlage,
        erfassungsgrundlage=record.erfassungsgrundlage,
        ausweisung=record.ausweisung,
        bearbeitungsstand=record.bearbeitungsstand,
        info_kontakt=record.info_kontakt,
        info=record.info,
        idherkunft=record.idherkunft,
    )
    return record.model_copy(
        update={"psets": {Pset_Objektinformation_Wasserschutzgebiet.pset_name: pset}}
    )


def records_from_geojson_feature_collection(
    data: dict[str, Any],
    *,
    geometry_crs: GeometryCrs = "EPSG:25832",
) -> List[WasserschutzgebietRecord]:
    """Parse a GeoJSON FeatureCollection dict into :class:`WasserschutzgebietRecord` list.

    Skips features without ``Polygon`` geometry or empty rings.

    Args:
        data: GeoJSON FeatureCollection object.
        geometry_crs: CRS of the polygon coordinates (``EPSG:25832`` or ``EPSG:4326``).
    """
    ensure_feature_collection(data)
    out: List[WasserschutzgebietRecord] = []
    for feat in iter_geojson_features(data):
        ring = parse_feature_polygon_exterior_ring(feat)
        if ring is None:
            continue
        props_raw = geojson_feature_properties(feat)
        if props_raw is None:
            continue
        fid = feature_identifier(feat, fallback=f"feature_{len(out)}")
        payload = {
            **props_raw,
            "feature_id": fid,
            "exterior_ring": ring,
            "geometry_crs": geometry_crs,
        }
        out.append(_record_with_psets_from_payload(payload))
    return out


def load_wasserschutzgebiete_records(
    path: Union[str, Path],
    *,
    geometry_crs: GeometryCrs = "EPSG:25832",
) -> List[WasserschutzgebietRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, geometry_crs=geometry_crs)


__all__ = [
    "GeometryCrs",
    "WasserschutzgebietRecord",
    "collect_wasserschutz_psets",
    "load_wasserschutzgebiete_records",
    "records_from_geojson_feature_collection",
]
