"""ALKIS Flurstuecke — cadastral parcels for the flurstuecke app.

Parsed from GeoJSON ``FeatureCollection`` responses such as
``/datasets/v1/alkis_vereinfacht/collections/Flurstueck/items``.
Geometry is ``MultiPolygon`` (a parcel may be multi-part); only exterior
rings are kept.

Vertex coordinates are either **EPSG:25832** ``(easting, northing)`` (default,
the collection ``storageCrs``) or **EPSG:4326** ``(lon, lat)`` — set
``geometry_crs`` when parsing.

Only the API fields that carry information are modelled. ``flur``,
``flstnrnen`` and ``abwrecht`` exist in the collection schema but are empty for
every Hamburg parcel (Hamburg keeps no Fluren), and ``land`` / ``landschl`` /
``regbezirk`` / ``kreis`` / ``gemeinde`` and their ``*schl`` counterparts are
constant for the whole city — none of them are modelled here.

Like :class:`StreetRecord` / :class:`WasserschutzgebietRecord`, each record
carries IFC pset templates under ``psets``.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from BIMFabrikHH_core.core.ogc_extractor import (
    OgcGeometryCrs,
    ensure_feature_collection,
    feature_identifier,
    geojson_feature_properties,
    iter_geojson_features,
    parse_feature_polygon_exterior_rings,
)

logger = logging.getLogger(__name__)


class FlurstueckRecord(BaseModel):
    """One ALKIS Flurstueck: exterior rings + API attributes + optional psets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")
    rings: List[List[Tuple[float, float]]] = Field(
        description="Exterior ring per MultiPolygon part; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    geometry_crs: OgcGeometryCrs = Field(
        default="EPSG:25832",
        description="CRS of ``rings`` vertex coordinates",
    )

    oid: str = Field(default="", description="ALKIS Objekt-ID (``idflurst`` plus ``FL`` suffix)")
    idflurst: str = Field(default="", description="ALKIS-Identifikator des Flurstücks → ``_ALKISIdentifikator``")
    flaeche: Optional[float] = Field(default=None, description="Amtliche Fläche in m² → ``_AmtlicheFlaeche``")
    flstkennz: str = Field(default="", description="20-stelliges Flurstückskennzeichen → ``_Flurstueckkennzeichen``")
    gemarkung: str = Field(default="", description="Name der Gemarkung → ``_GemarkungName``")
    gemaschl: str = Field(default="", description="Gemarkungsschlüssel (6-stellig)")
    flstnrzae: str = Field(default="", description="Flurstücksnummer, Zähler")
    aktualit: str = Field(default="", description="Aktualitätsdatum ``YYYY-MM-DDZ`` → ``_LZIbeginnt``")
    lagebeztxt: str = Field(default="", description="Lagebezeichnung (Straßenname[n])")
    tntxt: str = Field(default="", description="Tatsächliche Nutzung als ``Art/Unterart;Fläche``, ``|``-getrennt")

    psets: Dict[str, BaseModel] = Field(default_factory=dict)

    @property
    def element_name(self) -> str:
        """IFC element name: ``Flurstueck_{Gemarkung}_{Zähler}``, else kennzeichen / id."""
        gemarkung = (self.gemarkung or "Flurstueck").replace(" ", "_")
        if self.flstnrzae:
            return f"Flurstueck_{gemarkung}_{self.flstnrzae}"[:120]
        if self.flstkennz:
            return f"Flurstueck_{self.flstkennz}"[:120]
        return f"Flurstueck_{self.feature_id}"[:120]

    @property
    def element_color(self) -> Tuple[int, int, int]:
        """Stable pastel RGB from the Gemarkung name (MD5 hue, no name table)."""
        key = (self.gemarkung or "").strip() or "Flurstueck"
        digest = hashlib.md5(key.encode("utf-8")).digest()
        hue = int.from_bytes(digest[:2], "big") / 65535.0
        sat = 0.32 + (digest[2] / 255.0) * 0.18
        val = 0.86 + (digest[3] / 255.0) * 0.10
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        return int(r * 255), int(g * 255), int(b * 255)

    @property
    def element_bemerkung(self) -> str:
        """``_Bemerkung``: Gemarkung first, then Lagebezeichnung (or ``undefiniert``)."""
        lage = (self.lagebeztxt or "").strip() or "undefiniert"
        name = (self.gemarkung or "").strip()
        if not name:
            return lage
        return f"{name}; {lage}"

    @property
    def element_lzibeginnt(self) -> str:
        """``_LZIbeginnt`` from ``aktualit`` as ``YYYY-MM-DD`` (no time)."""
        value = (self.aktualit or "").strip()
        if not value:
            return "undefiniert"
        if "T" in value:
            value = value.split("T", 1)[0]
        return value.removesuffix("Z")


def collect_flurstueck_psets(
    record: FlurstueckRecord,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Extract Pydantic pset templates stored on :class:`FlurstueckRecord` (cf. streets)."""
    if not include_property_sets or not record.psets:
        return []
    out: List[BaseModel] = []
    for pset_name, value in record.psets.items():
        if isinstance(value, BaseModel):
            out.append(value)
        else:
            logger.warning(
                "Flurstueck %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                record.feature_id,
                pset_name,
                type(value).__name__,
            )
    return out


def _record_with_psets_from_payload(payload: Dict[str, Any]) -> FlurstueckRecord:
    record = FlurstueckRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_flurstuecke import (
        Pset_Objektinformation_Flurstueck,
    )

    pset = Pset_Objektinformation_Flurstueck(
        alkisidentifikator=record.idflurst,
        amtlicheflaeche=(record.flaeche, "m**2") if record.flaeche is not None else None,
        flurstueckkennzeichen=record.flstkennz,
        gemarkungname=record.gemarkung,
        lzibeginnt=record.element_lzibeginnt,
        bemerkung=record.element_bemerkung,
    )
    return record.model_copy(update={"psets": {Pset_Objektinformation_Flurstueck.pset_name: pset}})


def records_from_geojson_feature_collection(
    data: Dict[str, Any],
    *,
    geometry_crs: OgcGeometryCrs = "EPSG:25832",
) -> List[FlurstueckRecord]:
    """Parse a GeoJSON FeatureCollection into :class:`FlurstueckRecord` list.

    Skips features without polygon geometry or with empty rings.

    Args:
        data: GeoJSON FeatureCollection object.
        geometry_crs: CRS of the vertex coordinates (``EPSG:25832`` or ``EPSG:4326``).
    """
    ensure_feature_collection(data)
    out: List[FlurstueckRecord] = []
    for feat in iter_geojson_features(data):
        rings = parse_feature_polygon_exterior_rings(feat)
        if not rings:
            continue
        props_raw = geojson_feature_properties(feat)
        if props_raw is None:
            continue
        fid = feature_identifier(feat, fallback=f"feature_{len(out)}")
        payload = {
            **props_raw,
            "feature_id": fid,
            "rings": rings,
            "geometry_crs": geometry_crs,
        }
        out.append(_record_with_psets_from_payload(payload))
    return out


def load_flurstuecke_records(
    path: Union[str, Path],
    *,
    geometry_crs: OgcGeometryCrs = "EPSG:25832",
) -> List[FlurstueckRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, geometry_crs=geometry_crs)


__all__ = [
    "FlurstueckRecord",
    "collect_flurstueck_psets",
    "load_flurstuecke_records",
    "records_from_geojson_feature_collection",
]
