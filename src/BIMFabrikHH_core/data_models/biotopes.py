"""
Data models for biotope records.

Parsed from GeoJSON FeatureCollection from the Biotopkataster Hamburg API, with additional properties and optional psets for IFC export.

Geometry is stored as MultiPolygon, LineString or Point, depending on the biotope's shape type.
Vertex coordinates are kept as delivered; their CRS is declared by the caller via ``RequestParams.source_epsg``.

Biotope codes and descriptions are mapped from the Biotopkataster Hamburg API and the Bundeskompensationsverordnung (BKompV) using JSON mapping files in ``assets/``.

Each record carries IFC pset templates under ``psets``.
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import logging
from datetime import datetime
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from BIMFabrikHH_core.apps.boreholes.helper import _clean
from BIMFabrikHH_core.core.ogc_extractor import (
    MultiPolygon,
    ensure_feature_collection,
    feature_geometry_type,
    feature_identifier,
    geojson_feature_properties,
    iter_geojson_features,
    parse_feature_for_all_polygon_rings,
    parse_feature_multilinestring_paths,
    parse_feature_point,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BIOTOPE_HH_DESCRIPTIONS_FILE = "biotope_descriptions_HH.json"
_BIOTOPE_HH_BKOMPV_FILE = "biotope_code_HH_to_BKompV.json"
_BIOTOPE_BKOMPV_DESCRIPTIONS_FILE = "biotope_descriptions_BKompV.json"

_BIOTOP_BEWERTUNG_HH = "Biotopbewertung für die Biotopkartierung Hamburg"

UNDEFINED = "undefiniert"


# Source: https://www.hamburg.de/resource/blob/1079968/2b87716c8f78cfc971df24d34d837b7e/biotopbewertung-juli-2025-data.pdf
BEWERTUNG_DICT = {
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


class BiotopeShape(Enum):
    NONE = 0
    POINT = 1
    LINES = 2
    AREA = 3


class BiotopeRecord(BaseModel):
    """One Biotopkataster biotope: geometry (polygon/lines/point) + API attributes + optional psets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")

    shape_type: BiotopeShape = Field(
        default=BiotopeShape.NONE, description="Indicates whether the biotope geometry is a polygon, line or point."
    )

    polygons: MultiPolygon | None = Field(
        default=None,
        description="Multipolygon geometry: Exterior ring and holes per MultiPolygon part; (easting, northing) if EPSG:25832 else (lon, lat)",
    )
    lines: List[List[Tuple[float, float]]] | None = Field(
        default=None,
        description="Line geometry: list of (multiple) lines of coordinate tuples; (easting, northing) if EPSG:25832 else (lon, lat)",
    )
    point: Tuple | None = Field(
        default=None, description="Point geometry: Coordinate tuple; (easting, northing) if EPSG:25832 else (lon, lat)"
    )

    objectid: int = Field(description="Biotopkataster Objekt-ID")
    id_biotop: int = Field(
        description="ID-Biotop: Unique number under which the biotope is listed.",
    )
    dk5: int = Field(
        description="DK5: Tile number of the 1:5,000 digital map.",
    )
    biotop_nr: int = Field(description="Biotop-Nr.: Biotope number. Each biotope number is unique within a DK5 tile.")
    abschnitt: Optional[int] = Field(
        default=1,
        description="Abschnitt: A biotope may consist of several sections. This is the number of the respective section.",
    )

    biotop_erfasst_am: str = Field(default="", description="Biotop erfasst am: Date the biotope was mapped.")
    is_protected: bool = Field(default="", description="Indicates whether the biotope is protected by law.")

    hauptbiotoptyp: str = Field(default="", description="Hauptbiotoptyp: Primary biotope type of the biotope.")
    nebenbiotoptypen: str = Field(
        default="",
        description="Nebenbiotoptypen: A biotope may consist of several biotope types. In these cases, the additional biotope types are listed here.",
    )

    paragraf: str = Field(
        default="", description="gesetzl. Schutz: The paragraph based on which this biotope is protected by law."
    )
    schutzstatus_teilweise: Optional[str] = Field(
        default=None,
        description="Schutzstatus anteilig: This field indicates if the biotope is only partially protected by law.",
    )
    gesamtbewertung: Optional[int] = Field(
        default=None,
        description="Gesamtbewertung: The evaluation of the biotope according to the methodology of the statewide biotope mapping, from 1 to 9.",
    )

    code_ffh_lebensraumtyp_bfn: Optional[str] = Field(
        default=None,
        description="Code des FFH-Lebensraumtyps: Habitat type as defined by the Fauna-Flora-Habitatrichtlinie, provided that the biotope meets the criteria.",
    )

    erhaltungszustand_bfn: Optional[str] = Field(
        default=None, description="Erhaltungsgrad: Assessment of the conservation status of the FFH habitat type."
    )

    erhaltungszustand_bfn_abw: Optional[str] = Field(
        default=None,
        description="Erhaltungsgrad abweichend: Assessment of the conservation status of the FFH habitat type, if it differs from the standard assessment.",
    )

    ffh_entwicklungspotential: Optional[str] = Field(
        default=None,
        description="FFH-Entwicklungspotenzial: A habitat type under the Fauna-Flora-Habitatrichtlinie, provided that the biotope has the potential to meet the criteria in the future.",
    )

    flaeche_oder_laenge: Optional[float] = Field(default=None, description="Fläche oder Länge: Area (m²) or Length (m)")
    breite_lineares_objekt: Optional[float] = Field(
        default=None, description="Breite lineares Objekt: Width (m) of the linear biotope"
    )

    biotopbogen: str = Field(
        default="", description="Link to the Biotopbogen (biotope profile) for the respective biotope."
    )

    aktualitaet: str = Field(default="", description="Aktualität: Status of biotope mapping for the entire layer.")
    naechste_kartierung: Optional[int] = Field(
        default="",
        description="nächste Kartierung voraussichtlich: The year in which the biotope is expected to be mapped next.",
    )
    aufnahmetyp: str = Field(default="", description="Aufnahmetyp: Recording type of the selected object.")
    gruppe: str = Field(default="", description="Main group of biotope types to which this biotope belongs.")

    psets: Dict[str, BaseModel] = Field(default_factory=dict)

    @property
    def element_name(self) -> str:
        """IFC element name: ``Biotop_{id_biotop}``, else ``Biotop_{dk5}_{biotop_nr}``, else ``Biotop_{feature_id}``."""
        shape = self.shape_type.name.lower() if self.shape_type is not None else "biotope"

        if self.id_biotop is not None:
            return f"Biotop_{shape}_{self.id_biotop}"[:120]
        elif self.dk5 is not None and self.biotop_nr is not None:
            return f"Biotop_{shape}_{self.dk5}_{self.biotop_nr}"[:120]
        else:
            return f"Biotop_{shape}_{self.feature_id}"[:120]

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
def load_biotope_hh_to_bkompv_mapping() -> Dict[str, str]:
    """Load the table mapping Hamburg biotope type codes to their corresponding Bundeskompensationsverordnung (BKompV)
      codes, based on (https://www.bfn.de/eingriffsregelung-und-bundeskompensationsverordnung,
    "Übersetzungsschlüssel der Biotoptypen und -werte der Länder und deren Erläuterungen");
    empty dict when the file is missing.
    """
    return _load_config_json(_BIOTOPE_HH_BKOMPV_FILE)


@lru_cache(maxsize=1)
def load_biotope_hh_descriptions_mapping() -> Dict[str, str]:
    """Load the table mapping Hamburg biotope type codes to their descriptions, based on
    (https://www.bfn.de/eingriffsregelung-und-bundeskompensationsverordnung,
    "Übersetzungsschlüssel der Biotoptypen und -werte der Länder und deren Erläuterungen");
    empty dict when the file is missing.
    """
    return _load_config_json(_BIOTOPE_HH_DESCRIPTIONS_FILE)


@lru_cache(maxsize=1)
def load_biotope_bkompv_descriptions_mapping() -> Dict[str, str]:
    """Load the table mapping BKompV biotope type codes to their descriptions, based on
    (https://www.bfn.de/eingriffsregelung-und-bundeskompensationsverordnung,
    "Liste der Biotoptypen und -werte nach Anlage 2 BKompV im Excel-Format");
    empty dict when the file is missing.
    """
    return _load_config_json(_BIOTOPE_BKOMPV_DESCRIPTIONS_FILE)


def map_biotope_type_hh_descriptions(biotope_code: str, biotope_mapping: Optional[Dict[str, str]] = None) -> str:
    """Map a Hamburg biotope type code to its description, e.g. "NRT" -> "Schilf-Röhricht der Tide-Elbe".

    Args:
        biotope_code: biotope code used by the Biotopkataster Hamburg.
        biotope_mapping: Table from :func:`load_biotope_hh_to_bkompv_mapping`

    Returns:
        Biotope description string.
    """
    text = _clean(biotope_code)
    mapping = biotope_mapping if biotope_mapping is not None else load_biotope_hh_descriptions_mapping()

    return mapping.get(text, "")


def map_biotope_type_bkompv_descriptions(biotope_code: str, biotope_mapping: Optional[Dict[str, str]] = None) -> str:
    """Map a BKompV biotope type code to its description, e.g. "38.02.01" -> "Schilf-Wasserröhricht".

    Args:
        biotope_code: biotope code used by the BKompV.
        biotope_mapping: Table from :func:`load_biotope_bkompv_descriptions_mapping`

    Returns:
        Biotope description string.
    """
    text = _clean(biotope_code)
    mapping = biotope_mapping if biotope_mapping is not None else load_biotope_bkompv_descriptions_mapping()

    return mapping.get(text, "")


def map_biotope_type_bkompv_codes(biotope_code: str, biotope_mapping: Optional[Dict[str, str]] = None) -> str:
    """Map a Hamburg biotope type code to its corresponding BKompV code, e.g. "NRT" -> "38.02.01".

    Args:
        biotope_code: biotope code used by the Biotopkataster Hamburg.
        biotope_mapping: Table from :func:`load_biotope_hh_to_bkompv_mapping`

    Returns:
        Biotope code used in the BKompV.
    """
    text = _clean(biotope_code)
    mapping = biotope_mapping if biotope_mapping is not None else load_biotope_hh_to_bkompv_mapping()

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


def _combine_haupt_and_neben_biotopes(haupt: str, neben: list[str] = []):
    """Build a combined string of primary and secondary bioptopes in the format ``Hauptbiotop (Nebenbiotop1; Nebenbiotop2; ...)``."""
    if not haupt:
        return ""
    if not neben or not any(neben):
        return str(haupt)
    else:
        neben_unique = list(dict.fromkeys(neben))
        neben_str = "; ".join(map(str, neben_unique))
        return f"{str(haupt)} ({neben_str})"


def _record_with_psets_from_payload(payload: Dict[str, Any], biotope_name_mapping: Dict[str, str]) -> BiotopeRecord:
    record = BiotopeRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import Pset_Objektinformation_Biotop

    hauptbiotoptyp_land_code = record.hauptbiotoptyp
    hauptbiotoptyp_land_name = map_biotope_type_hh_descriptions(hauptbiotoptyp_land_code, biotope_name_mapping)
    nebenbiotoptyp_land_codes: List[str] = [
        nebenbiotoptyp.strip() for nebenbiotoptyp in record.nebenbiotoptypen.split(",")
    ]
    nebenbiotoptyp_land_names: List[str] = [
        map_biotope_type_hh_descriptions(nebenbiotoptyp_code, biotope_name_mapping)
        for nebenbiotoptyp_code in nebenbiotoptyp_land_codes
    ]

    biotoptyp_land_code_combined = _combine_haupt_and_neben_biotopes(
        hauptbiotoptyp_land_code, nebenbiotoptyp_land_codes
    )
    biotoptyp_land_name_combined = _combine_haupt_and_neben_biotopes(
        hauptbiotoptyp_land_name, nebenbiotoptyp_land_names
    )

    hauptbiotoptyp_bkompv_code = map_biotope_type_bkompv_codes(hauptbiotoptyp_land_code)
    hauptbiotoptyp_bkompv_name = map_biotope_type_bkompv_descriptions(hauptbiotoptyp_bkompv_code)
    nebenbiotoptyp_bkompv_codes: List[str] = [
        map_biotope_type_bkompv_codes(land_code) for land_code in nebenbiotoptyp_land_codes
    ]
    nebenbiotoptyp_bkompv_names: List[str] = [
        map_biotope_type_bkompv_descriptions(bkompv_code) for bkompv_code in nebenbiotoptyp_bkompv_codes
    ]

    biotoptyp_bkompv_code_combined = _combine_haupt_and_neben_biotopes(
        hauptbiotoptyp_bkompv_code, nebenbiotoptyp_bkompv_codes
    )
    biotoptyp_bkompv_name_combined = _combine_haupt_and_neben_biotopes(
        hauptbiotoptyp_bkompv_name, nebenbiotoptyp_bkompv_names
    )

    protection_status_landesrecht = (
        "nicht geschützt"
        if not record.is_protected
        else (
            "teilweise geschützt"
            if record.schutzstatus_teilweise is not None and record.schutzstatus_teilweise.strip().lower() == "ja"
            else (
                " vollständig geschützt"
                if record.schutzstatus_teilweise is None or record.schutzstatus_teilweise.strip().lower() == "nein"
                else str(record.schutzstatus_teilweise)
            )
        )
    )

    try:
        kartierung_jahr = str(datetime.strptime(record.biotop_erfasst_am, "%d.%m.%Y").year)
    except ValueError:
        kartierung_jahr = UNDEFINED

    pset_objektinfo = Pset_Objektinformation_Biotop(
        kartierung_jahr=kartierung_jahr,
        biotopnummer=record.id_biotop,  # id_biotop is unique, in contrast to biotop_nr.
        abschnitt_nr=record.abschnitt,
        biotoptyp_bkompv_code=biotoptyp_bkompv_code_combined or UNDEFINED,
        biotoptyp_bkompv_name=biotoptyp_bkompv_name_combined or UNDEFINED,
        biotoptyp_land_code=biotoptyp_land_code_combined or UNDEFINED,
        biotoptyp_land_name=biotoptyp_land_name_combined or UNDEFINED,
        biotop_gesamtwert=str(record.gesamtbewertung),
        biotop_gesamtwert_bedeutung=BEWERTUNG_DICT.get(str(record.gesamtbewertung), UNDEFINED),
        biotop_gesamtwert_liste=str(_BIOTOP_BEWERTUNG_HH),
        gefaehrdung_status=record.erhaltungszustand_bfn or record.erhaltungszustand_bfn_abw or UNDEFINED,
        ist_gesetzl_gesch_biotop=record.is_protected,
        ist_gesetzl_gesch_biotop_landesrecht=protection_status_landesrecht,
        # TODO: writing "ha", it gets converted to m**2. -> Find out how to display in ha.
        biotop_groesse_ha=((record.flaeche_oder_laenge, "m**2") if record.flaeche_oder_laenge is not None else None),
        ist_ffh_lebensraum=record.code_ffh_lebensraumtyp_bfn is not None,
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
    is_protected: bool,
) -> List[BiotopeRecord]:
    """Parse a GeoJSON FeatureCollection into :class:`BiotopeRecord` list.

    Skips features without polygon geometry or with empty rings.

    Args:
        data: GeoJSON FeatureCollection object.
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
            "is_protected": is_protected,
            "shape_type": shape_type,
        }

        biotope_types = load_biotope_hh_descriptions_mapping()
        out.append(_record_with_psets_from_payload(payload, biotope_name_mapping=biotope_types))
    return out


def load_biotope_records(path: Union[str, Path], *, is_protected: bool) -> List[BiotopeRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, is_protected=is_protected)


__all__ = [
    "BiotopeRecord",
    "collect_biotope_psets",
    "load_biotope_records",
    "records_from_geojson_feature_collection",
]
