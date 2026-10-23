"""
Biotopkataster - extensive biotopes (Flächenhafte Biotope).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
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
    MultiPolygon,
    OgcGeometryCrs, 
    ensure_feature_collection, 
    feature_identifier,
    geojson_feature_properties, iter_geojson_features,
    parse_feature_for_all_polygon_rings,
    parse_feature_multilinestring_paths,
    parse_feature_point,
    feature_geometry_type)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BIOTOPE_MAPPING_FILE = "biotope_mapping_HH.json"
UNDEFINED = "undefiniert"

class BiotopeShape(Enum):
    NONE = 0
    POINT = 1
    LINES = 2
    AREA = 3

class BiotopeRecord(BaseModel):
    """One Biotopkataster biotope: geometry (polygon/lines/point) + API attributes + optional psets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")

    geometry_crs: OgcGeometryCrs = Field(
        default="EPSG:25832",
        description="CRS of vertex coordinates",
    )

    shape_type: BiotopeShape = Field(
        description="Indicates whether the habitat geometry is a polygon, line or point."
    )

    polygons: MultiPolygon | None = Field(
        description="Multipolygon geometry: Exterior ring and holes per MultiPolygon part; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    lines: List[List[Tuple[float, float]]] | None = Field(
        description="Line geometry: list of (multiple) lines of coordinate tuples; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    point: Tuple | None = Field(
        description="Point geometry: Coordinate tuple; (easting, northing) if EPSG:25832 else (lon, lat)"
    )

    # TODO: Add descriptions
    objectid: int = Field(description="Biotopkataster Objekt-ID (TODO: Definition)")
    id_biotop: int = Field(description="TODO",)
    dk5: int = Field(description="TODO",)
    biotop_nr: int = Field(description="TODO",)
    abschnitt: Optional[int] = Field(description="TODO",)

    biotop_erfasst_am: str = Field(description="TODO",
        default="",
    )
    is_protected: bool = Field(description="Indicates whether the habitat is protected by law.")
    hauptbiotoptyp: str = Field(description="TODO",
        default="",
    )
    nebenbiotoptypen: str = Field(description="TODO",
        default="",
    )
    paragraf: str = Field(description="TODO",
        default="",
    )
    schutzstatus_teilweise: Optional[str] = Field(description="TODO",
        default=None,
    )
    gesamtbewertung: Optional[int] = Field(description="TODO", default=None)
    
    code_ffh_lebensraumtyp_bfn: Optional[str] = Field(description="TODO", default=None)

    flaeche_oder_laenge: Optional[float] = Field(description="TODO", default=None)
    breite_lineares_objekt: Optional[float] = Field(description="TODO", default=None)
    biotopbogen: str = Field(description="TODO",
        default="",
    )
    aktualitaet: str = Field(description="TODO",
        default="",
    )
    naechste_kartierung: Optional[int] = Field(description="TODO",)
    aufnahmetyp: str = Field(description="TODO",
        default="",
    )
    gruppe: str = Field(description="TODO",
        default="",
    )

    psets: Dict[str, BaseModel] = Field(description="TODO", default_factory=dict)

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


def build_biotope_hyperlink(url: str, id_biotop: int) -> Pset_Hyperlink:
    """Build the  link to a biotope's Biotopkataster Erhebungsbogen.

    Args:
        url: "biotopbogen" link from the biotope dataset
        id_biotop: Unique database id of the biotope


    Returns:
        ``Pset_Hyperlink`` with the URL and a German remark.
    """
    if url:
        bemerkung = f"Link zum Erhebungsbogen für Biotop {id_biotop}."
    else:
        bemerkung = f"Kein Erhebungsbogen verfügbar für Biotop {id_biotop}."
    return Pset_Hyperlink(hyperlink_001=url, hyperlink_001_bemerkung=bemerkung)


def _combine_haupt_and_neben_biotopes(haupt: str, neben: str = None):
    if not neben:
        return str(haupt)
    else:
        neben_unique = list(dict.fromkeys(neben))
        neben_str = '; '.join(map(str, set(neben_unique)))
        return f"{str(haupt)} ({neben_str})"


def _record_with_psets_from_payload(payload: Dict[str, Any], biotope_name_mapping: Dict[str, str]) -> BiotopeRecord:
    record = BiotopeRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import \
        Pset_Objektinformation_Biotop

    hauptbiotoptyp_code = record.hauptbiotoptyp
    hauptbiotoptyp_name = map_biotope_type(hauptbiotoptyp_code, biotope_name_mapping)
    nebenbiotoptyp_codes: List[str] = [nebenbiotoptyp.strip() for nebenbiotoptyp in record.nebenbiotoptypen.split(",")]
    nebenbiotoptyp_names: List[str] = [map_biotope_type(nebenbiotoptyp_code, biotope_name_mapping) for nebenbiotoptyp_code in nebenbiotoptyp_codes]

    biotoptyp_land_code_combined = _combine_haupt_and_neben_biotopes(hauptbiotoptyp_code,  nebenbiotoptyp_codes)
    biotoptyp_land_name_combined = _combine_haupt_and_neben_biotopes(hauptbiotoptyp_name, nebenbiotoptyp_names)

    # Source: https://www.hamburg.de/resource/blob/1079968/2b87716c8f78cfc971df24d34d837b7e/biotopbewertung-juli-2025-data.pdf 
    # TODO: load and store somewhere 
    bewertung_dict = {
        "1": "weitgehend unbelebt",
        "2": "extrem verarmt",
        "3": "stark verarmt",
        "4": "verarmt",
        "5": "noch wertvoll",
        "6": "wertvoll",
        "7": "besonders wertvoll",
        "8": "hochgradig wertvoll",
        "9": "herausragend",
    }

    protection_status_landesrecht = (
        "nicht geschützt"
        if not record.is_protected
        else "teilweise geschützt" if record.schutzstatus_teilweise else " vollständig geschützt"
    )

    try:
        kartierung_jahr = str(datetime.strptime(record.biotop_erfasst_am, '%d.%m.%Y').year)
    except ValueError:
        kartierung_jahr = UNDEFINED

    pset_objektinfo = Pset_Objektinformation_Biotop(
        kartierung_jahr = kartierung_jahr,
        biotopnummer=record.id_biotop,  # id_biotop is unique, in contrast to biotop_nr.
        abschnitt_nr=record.abschnitt,  #  TODO: is "abschnitt" the number of section or the number of the section?
        # biotoptyp_bkompv_code="",
        # biotoptyp_bkompv_land="",
        biotoptyp_land_code=biotoptyp_land_code_combined,
        biotoptyp_land_name=biotoptyp_land_name_combined,
        biotop_gesamtwert=str(record.gesamtbewertung),
        biotop_gesamtwert_bedeutung=bewertung_dict.get(str(record.gesamtbewertung), UNDEFINED),
        # biotop_gesamtwert_liste="",  # TODO Bezeichnung bzw. Referenz des verwendeten Bewertungsverfahrens für den Biotopgesamtwert.
        # gefaehrdung_status="",  # TODO find status info
        ist_gesetzl_gesch_biotop=record.is_protected,
        ist_gesetzl_gesch_biotop_landesrecht=protection_status_landesrecht,
        # Convert m^2 to ha
        biotop_groesse_ha=(
            (record.flaeche_oder_laenge / 10000.0, "ha") if record.flaeche_oder_laenge is not None else None
        ),
        ist_ffh_lebensraum=record.code_ffh_lebensraumtyp_bfn is not None
    )

    pset_hyperlink = build_biotope_hyperlink(url=record.biotopbogen, id_biotop=record.id_biotop)

    return record.model_copy(
        update={
            "psets": {
                Pset_Objektinformation_Biotop.pset_name: pset_objektinfo,
                Pset_Hyperlink.pset_name: pset_hyperlink,
            }
        }
    )


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
        geom_type = feature_geometry_type(feat)
        polygons = lines = point = None
        if not geom_type:
            continue
        shape_type = BiotopeShape.NONE
        if geom_type in ["MultiPolygon", "Polygon"]:
            shape_type = BiotopeShape.AREA
            polygons = parse_feature_for_all_polygon_rings(feat)
            if not polygons:
                continue
        elif geom_type == "MultiLineString":
            shape_type = BiotopeShape.LINES
            lines = parse_feature_multilinestring_paths(feat)
            if not lines:
                continue
        elif geom_type == "Point":
            shape_type = BiotopeShape.POINT
            point = parse_feature_point(feat)
            if not point:
                continue
        else:
            continue

        props_raw = geojson_feature_properties(feat)
        if props_raw is None:
            continue
        fid = feature_identifier(feat, fallback=f"feature_{len(out)}")
        payload = {
            **props_raw,
            "feature_id": fid,
            "polygons": polygons,
            "lines": lines,
            "point": point,
            "geometry_crs": geometry_crs,
            "is_protected": is_protected,
            "shape_type": shape_type,
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
