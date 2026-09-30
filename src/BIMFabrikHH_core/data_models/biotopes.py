"""
Biotopkataster - extensive biotopes (Flächenhafte Biotope).
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from BIMFabrikHH_core.apps.boreholes.helper import _clean
from BIMFabrikHH_core.core.ogc_extractor import (
    OgcGeometryCrs, ensure_feature_collection, feature_identifier,
    geojson_feature_properties, iter_geojson_features,
    parse_feature_polygon_exterior_rings)

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BIOTOPE_MAPPING_FILE = "biotope_mapping_HH.json"
UNDEFINED = "undefiniert"


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
    objectid: int = Field(description="Biotopkataster Objekt-ID (TODO: Definition)")
    id_biotop: int = Field()
    dk5: int = Field()
    biotop_nr: int = Field()
    is_protected: bool = Field(description="Indicates whether the habitat is protected by law.")
    abschnitt: Optional[int] = Field()
    hauptbiotoptyp: str = Field(
        default="",
    )
    nebenbiotoptypen: str = Field(
        default="",
    )
    paragraf: str = Field(
        default="",
    )
    schutzstatus_teilweise: Optional[str] = Field(
        default=None,
    )
    gesamtbewertung: int = Field()
    flaeche_oder_laenge: float = Field()
    biotopbogen: str = Field(
        default="",
    )
    aktualitaet: str = Field(
        default="",
    )
    naechste_kartierung: Optional[int] = Field()
    aufnahmetyp: str = Field(
        default="",
    )
    gruppe: str = Field(
        default="",
    )

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


def _load_config_json(filename: str) -> Dict[str, Any]:
    path = ASSETS_DIR / filename
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Mapping file missing: %s", path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Mapping file %s could not be read: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=1)
def load_biotope_mapping() -> Dict[str, str]:
    """Load the biotope type table (https://www.bfn.de/eingriffsregelung-und-bundeskompensationsverordnung,
    "Übersetzungsschlüssel der Biotoptypen und -werte der Länder und deren Erläuterungen");
    empty dict when the file is missing.
    """
    return _load_config_json(_BIOTOPE_MAPPING_FILE)


def map_biotope_type(biotope_code: str, biotope_mapping: Optional[Dict[str, str]] = None) -> str:
    """Map a Hamburg biotope code to its description, e.g. "NRT" -> "Schilf-Röhricht der Tide-Elbe".

    Args:
        biotope_code: biotope code used by the Biotopkataster Hamburg.
        biotope_mapping: Table from :func:`load_biotope_mapping`

    Returns:
        Biotope description string.
    """
    text = _clean(biotope_code)
    mapping = biotope_mapping if biotope_mapping is not None else load_biotope_mapping()

    return mapping.get(text, "")


def _record_with_psets_from_payload(payload: Dict[str, Any], biotope_name_mapping: Dict[str, str]) -> BiotopeRecord:
    record = BiotopeRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import \
        Pset_Objektinformation_Biotop

    hauptbiotoptyp_name = map_biotope_type(record.hauptbiotoptyp, biotope_name_mapping)

    pset = Pset_Objektinformation_Biotop(
        biotopnummer=record.id_biotop,  # id_biotop is unique, in contrast to biotop_nr.
        abschnitt_nr=record.abschnitt,  #  TODO: is "abschnitt" the number of section or the number of the section?
        biotoptyp_land_code=record.hauptbiotoptyp,  #  TODO: Where to put nebenbiotoptypen?
        biotoptyp_land_name=hauptbiotoptyp_name,
        biotop_gesamtwert=str(record.gesamtbewertung),
        biotop_gesamtwert_liste="",  # TODO Bezeichnung bzw. Referenz des verwendeten Bewertungsverfahrens für den Biotopgesamtwert.
        biotop_gesamtwert_bedeutung="",  # TODO map to meaning
        gefaehrdung_status="",  # TODO find status info
        ist_gesetzl_gesch_biotop=record.is_protected,
        ist_gesetzl_gesch_biotop_landesrecht=(
            "nicht geschützt"
            if not record.is_protected
            else "teilweise geschützt" if record.schutzstatus_teilweise else " vollständig geschützt"
        ),
        # Convert m^2 to ha
        biotop_groesse_ha=(
            (record.flaeche_oder_laenge / 10000.0, "ha") if record.flaeche_oder_laenge is not None else None
        ),
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

        biotope_types = load_biotope_mapping()
        out.append(_record_with_psets_from_payload(payload, biotope_name_mapping=biotope_types))
    return out


def load_biotope_records(
    path: Union[str, Path], *, geometry_crs: OgcGeometryCrs = "EPSG:25832", is_protected: bool
) -> List[BiotopeRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, geometry_crs=geometry_crs, is_protected=is_protected)
