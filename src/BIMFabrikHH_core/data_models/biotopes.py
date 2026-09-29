"""
Biotopkataster - extensive biotopes (Flächenhafte Biotope).
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


class BiotopeRecord(BaseModel):
    """One Biotopkataster biotope: exterior rings + API attributes + optional psets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")
    rings: List[List[Tuple[float, float]]] = Field(
        description="Exterior ring per MultiPolygon part; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    geometry_crs: OgcGeometryCrs = Field(
        default="EPSG:25832",
        description="CRS of ``rings`` vertex coordinates",
    )

    # TODO: Add descriptions
    objectid:  int = Field(description="Biotopkataster Objekt-ID (TODO: Definition)")
    id_biotop: int = Field()
    dk5: int = Field()
    biotop_nr: int = Field()
    is_protected: bool = Field(description="Indicates whether the habitat is protected by law.")
    abschnitt: Optional[int] = Field()
    hauptbiotoptyp: str = Field(default="", )
    nebenbiotoptypen: str = Field(default="", )
    paragraf: str = Field(default="", )
    schutzstatus_teilweise: Optional[str] = Field(default=None, )
    gesamtbewertung: int = Field()
    flaeche_oder_laenge: float = Field()
    biotopbogen: str = Field(default="", )
    aktualitaet: str = Field(default="", )
    naechste_kartierung: Optional[int] = Field()
    aufnahmetyp: str = Field(default="", )
    gruppe: str = Field(default="", )

    psets: Dict[str, BaseModel] = Field(default_factory=dict)

    @property
    def element_name(self) -> str:
        """IFC element name: feature id. TODO: find good element name"""
        return f"Biotop_{self.feature_id}"[:120]

    @property
    def element_color(self) -> Tuple[int, int, int]:
        """Stable pastel RGB from the hauptbiotoptyp (MD5 hue, no name table)."""
        key = (self.hauptbiotoptyp or "").strip() or "Biotop"
        digest = hashlib.md5(key.encode("utf-8")).digest()
        hue = int.from_bytes(digest[:2], "big") / 65535.0
        sat = 0.32 + (digest[2] / 255.0) * 0.18
        val = 0.86 + (digest[3] / 255.0) * 0.10
        r, g, b = colorsys.hsv_to_rgb(hue, sat, val)
        return int(r * 255), int(g * 255), int(b * 255)



def collect_biotope_psets(
    record: BiotopeRecord,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Extract Pydantic pset templates stored on :class:`BiotopeRecord`."""
    if not include_property_sets or not record.psets:
        return []
    out: List[BaseModel] = []
    for pset_name, value in record.psets.items():
        if isinstance(value, BaseModel):
            out.append(value)
        else:
            logger.warning(
                "Biotope %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                record.feature_id,
                pset_name,
                type(value).__name__,
            )
    return out


def _record_with_psets_from_payload(payload: Dict[str, Any]) -> BiotopeRecord:
    record = BiotopeRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import (
        Pset_Objektinformation_Biotop,
    )

    pset = Pset_Objektinformation_Biotop(
        biotopnummer=record.biotop_nr, #TODO: check which number/id is the correct one here. id_biotop vs. biotop_nr?
        abschnitt_nr=record.abschnitt,
        biotoptyp_land_code=record.hauptbiotoptyp,
        biotoptyp_land_name="", # TODO map to name: Landesspezifische Bezeichnung des Biotoptyps.
        biotop_gesamtwert=str(record.gesamtbewertung),
        biotop_gesamtwert_liste="", # TODO Bezeichnung bzw. Referenz des verwendeten Bewertungsverfahrens für den Biotopgesamtwert.
        biotop_gesamtwert_bedeutung="", # TODO map to meaning
        gefaehrdung_status="", # TODO find status info
        ist_gesetzl_gesch_biotop=record.is_protected,
        ist_gesetzl_gesch_biotop_landesrecht="nicht geschützt" if not record.is_protected else "teilweise geschützt" if record.schutzstatus_teilweise else " vollständig geschützt",

        # Convert m^2 to ha
        biotop_groesse_ha=(record.flaeche_oder_laenge/1000.0, "ha") if record.flaeche_oder_laenge is not None else None,
    )
    return record.model_copy(update={"psets": {Pset_Objektinformation_Biotop.pset_name: pset}})


def records_from_geojson_feature_collection(
    data: Dict[str, Any],
    *,
    geometry_crs: OgcGeometryCrs = "EPSG:25832",
    is_protected: bool,
) -> List[BiotopeRecord]:
    """Parse a GeoJSON FeatureCollection into :class:`BiotopeRecord` list.

    Skips features without polygon geometry or with empty rings.

    Args:
        data: GeoJSON FeatureCollection object.
        geometry_crs: CRS of the vertex coordinates (``EPSG:25832`` or ``EPSG:4326``).
    """
    ensure_feature_collection(data)
    out: List[BiotopeRecord] = []
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
            "is_protected": is_protected,
        }
        out.append(_record_with_psets_from_payload(payload))
    return out


def load_biotope_records(
    path: Union[str, Path],
    *,
    geometry_crs: OgcGeometryCrs = "EPSG:25832",
    is_protected: bool
) -> List[BiotopeRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, geometry_crs=geometry_crs, is_protected=is_protected)