"""ALKIS Tatsächliche Nutzung — traffic surfaces for the streets app.

Parsed from GeoJSON ``FeatureCollection`` responses such as
``/datasets/v1/alkis_vereinfacht/collections/Nutzung/items``.
Geometry is ``Polygon`` / ``MultiPolygon``; only exterior rings are kept.
By default only the three traffic classes are accepted:

- ``Strassenverkehr``
- ``Weg``
- ``Bahnverkehr``

Vertex coordinates are either **EPSG:25832** ``(easting, northing)`` (default,
the collection ``storageCrs``) or **EPSG:4326** ``(lon, lat)`` — set
``geometry_crs`` when parsing.

Like :class:`WasserschutzgebietRecord` / :class:`TreeRecord`, each record carries
IFC pset templates under ``psets``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field

from BIMFabrikHH_core.core.ogc_extractor import (
    OgcGeometryCrs,
    ensure_feature_collection,
    feature_identifier,
    geojson_feature_properties,
    iter_geojson_features,
    parse_feature_polygon_exterior_rings,
)

GeometryCrs = OgcGeometryCrs

logger = logging.getLogger(__name__)

NUTZUNG_OAF_ITEMS = "https://api.hamburg.de/datasets/v1/alkis_vereinfacht/collections/Nutzung/items"
NUTZUNG_OAF_CRS = "http://www.opengis.net/def/crs/EPSG/0/25832"
ALKIS_NUTZUNG_WEITERE_GEOJSON = "alkis_nutzung_weitere.geojson"
ALKIS_NUTZUNG_VERKEHR_GEOJSON = "alkis_nutzung_verkehr.geojson"

DEFAULT_NUTZARTEN: FrozenSet[str] = frozenset({"Strassenverkehr", "Weg", "Bahnverkehr"})

# All Tatsächliche Nutzung classes used as DGM Bruchkanten (not Gebäude).
GUIDE_NUTZARTEN: FrozenSet[str] = frozenset(
    {
        "Strassenverkehr",
        "Weg",
        "Bahnverkehr",
        "Platz",
        "Wohnbauflaeche",
        "Industrie Und Gewerbeflaeche",
        "Flaeche Gemischter Nutzung",
        "Flaeche Besonderer Funktionaler Praegung",
        "Sport Freizeit Und Erholungsflaeche",
        "Fliessgewaesser",
        "Stehendes Gewaesser",
        "Hafenbecken",
        "Meer",
        "Schiffsverkehr",
        "Unland Vegetationslose Flaeche",
    }
)
WEITERE_NUTZARTEN: FrozenSet[str] = frozenset(GUIDE_NUTZARTEN - DEFAULT_NUTZARTEN)


def nutzung_split_label(nutzart: str, bez: str = "") -> str:
    """IFC / TIN split key: ``nutzart``, or ``nutzart|bez`` for street subtypes."""
    nutzart = (nutzart or "").strip()
    bez = (bez or "").strip()
    if nutzart == "Strassenverkehr" and bez:
        return f"{nutzart}|{bez}"
    return nutzart


def nutzung_idebene1(nutzart: str) -> str:
    """BIM.HH ``_IDEbene1`` bucket for an ALKIS ``nutzart``."""
    if nutzart in {"Strassenverkehr", "Weg", "Bahnverkehr", "Platz", "Schiffsverkehr"}:
        return "Verkehr"
    if nutzart in {"Fliessgewaesser", "Stehendes Gewaesser", "Hafenbecken", "Meer"}:
        return "Gewaesser"
    if nutzart == "Sport Freizeit Und Erholungsflaeche":
        return "Vegetation"
    return "Siedlung"


class StreetRecord(BaseModel):
    """One ALKIS Nutzung traffic surface: exterior rings + attributes + optional psets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    feature_id: Union[int, str] = Field(description="``feature.id`` from GeoJSON")
    rings: List[List[Tuple[float, float]]] = Field(
        description="Exterior rings; (easting, northing) if EPSG:25832 else (lon, lat)"
    )
    geometry_crs: GeometryCrs = Field(
        default="EPSG:25832",
        description="CRS of ``rings`` vertex coordinates",
    )

    oid: str = Field(default="", description="ALKIS object id")
    nutzart: str = Field(default="", description="Nutzungsart (Strassenverkehr / Weg / Bahnverkehr)")
    bez: str = Field(default="", description="Feinere Bezeichnung (z. B. Fahrbahn, Begleitfläche)")
    name: str = Field(default="", description="Optionaler Objektname")
    aktualit: str = Field(default="", description="Aktualitätsdatum der Nutzung")

    psets: Dict[str, BaseModel] = Field(default_factory=dict)


def collect_street_psets(
    record: StreetRecord,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Extract Pydantic pset templates stored on :class:`StreetRecord` (cf. wasserschutzgebiete)."""
    if not include_property_sets or not record.psets:
        return []
    out: List[BaseModel] = []
    for pset_name, value in record.psets.items():
        if isinstance(value, BaseModel):
            out.append(value)
        else:
            logger.warning(
                "Street %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                record.feature_id,
                pset_name,
                type(value).__name__,
            )
    return out


def _record_with_psets_from_payload(payload: Dict[str, Any]) -> StreetRecord:
    record = StreetRecord.model_validate(payload)
    from BIMFabrikHH_core.data_models.pydantic_psets_streets import (
        Pset_Objektinformation_Strasse,
    )

    pset = Pset_Objektinformation_Strasse(
        idebene1=nutzung_idebene1(record.nutzart),
        idebene2=record.nutzart or "Nutzung",
        idebene3=record.bez or record.nutzart or "Nutzung",
        nutzart=record.nutzart,
        bez=record.bez,
        name=record.name,
        oid=record.oid,
        aktualit=record.aktualit,
        bemerkung="ALKIS Tatsaechliche Nutzung",
    )
    return record.model_copy(update={"psets": {Pset_Objektinformation_Strasse.pset_name: pset}})


def pset_for_nutzung_group(records: Sequence[StreetRecord], *, label: str) -> "Pset_Objektinformation_Strasse":
    """One ``Pset_Objektinformation`` summarizing all features that share ``label``."""
    from BIMFabrikHH_core.data_models.pydantic_psets_streets import (
        Pset_Objektinformation_Strasse,
    )

    matching = [r for r in records if nutzung_split_label(r.nutzart, r.bez) == label]
    if not matching:
        matching = [r for r in records if r.nutzart == label]
    nutzart = matching[0].nutzart if matching else label.split("|", 1)[0]
    bezs = sorted({r.bez for r in matching if r.bez})
    names = sorted({r.name for r in matching if r.name})
    oids = [r.oid for r in matching if r.oid]
    dates = sorted({r.aktualit for r in matching if r.aktualit})
    oid_text = "; ".join(oids) if 0 < len(oids) <= 8 else f"{len(oids)} Features"
    return Pset_Objektinformation_Strasse(
        idebene1=nutzung_idebene1(nutzart),
        idebene2=nutzart or "Nutzung",
        idebene3=bezs[0] if len(bezs) == 1 else (nutzart or label),
        nutzart=nutzart,
        bez="; ".join(bezs),
        name="; ".join(names)[:240],
        oid=oid_text,
        aktualit="; ".join(dates),
        bemerkung=f"ALKIS Tatsaechliche Nutzung, {len(matching)} Flaeche(n)",
    )


def records_from_geojson_feature_collection(
    data: Dict[str, Any],
    *,
    geometry_crs: GeometryCrs = "EPSG:25832",
    nutzarten: Optional[FrozenSet[str]] = DEFAULT_NUTZARTEN,
) -> List[StreetRecord]:
    """Parse a GeoJSON FeatureCollection into :class:`StreetRecord` list.

    Skips features without polygon geometry, empty rings, or (when ``nutzarten``
    is set) a ``nutzart`` outside the allowed set.

    Args:
        data: GeoJSON FeatureCollection object.
        geometry_crs: CRS of the vertex coordinates (``EPSG:25832`` or ``EPSG:4326``).
        nutzarten: Allowed ``nutzart`` values. ``None`` keeps every Nutzung class.
    """
    ensure_feature_collection(data)
    out: List[StreetRecord] = []
    for feat in iter_geojson_features(data):
        rings = parse_feature_polygon_exterior_rings(feat)
        if not rings:
            continue
        props_raw = geojson_feature_properties(feat)
        if props_raw is None:
            continue
        nutzart = str(props_raw.get("nutzart") or "")
        if nutzarten is not None and nutzart not in nutzarten:
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


def load_streets_records(
    path: Union[str, Path],
    *,
    geometry_crs: GeometryCrs = "EPSG:25832",
    nutzarten: Optional[FrozenSet[str]] = DEFAULT_NUTZARTEN,
) -> List[StreetRecord]:
    """Load and parse a ``.json`` FeatureCollection from disk."""
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return records_from_geojson_feature_collection(data, geometry_crs=geometry_crs, nutzarten=nutzarten)


def _feature_nutzart(feature: Dict[str, Any]) -> str:
    props = geojson_feature_properties(feature) or {}
    return str(props.get("nutzart") or "")


def _filter_feature_collection(
    data: Dict[str, Any],
    *,
    nutzarten: FrozenSet[str],
) -> Dict[str, Any]:
    features = [f for f in iter_geojson_features(data) if _feature_nutzart(f) in nutzarten]
    return {"type": "FeatureCollection", "features": features, "numberReturned": len(features)}


def write_nutzung_geojson(
    data: Dict[str, Any],
    path: Union[str, Path],
    *,
    nutzarten: FrozenSet[str],
) -> Path:
    """Write a filtered FeatureCollection. Caller decides whether to invoke this."""
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload = _filter_feature_collection(data, nutzarten=nutzarten)
    dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %d Nutzung feature(s) → %s", payload["numberReturned"], dest)
    return dest


def fetch_nutzung_feature_collection(
    bbox_wgs84: Tuple[float, float, float, float],
    *,
    limit: int = 250,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Download ALKIS ``Nutzung`` items for a WGS84 bbox (coordinates in EPSG:25832)."""
    import requests

    features: List[Dict[str, Any]] = []
    offset = 0
    matched: Optional[int] = None
    while True:
        params = {
            "f": "json",
            "limit": limit,
            "offset": offset,
            "bbox": ",".join(str(v) for v in bbox_wgs84),
            "crs": NUTZUNG_OAF_CRS,
        }
        response = requests.get(NUTZUNG_OAF_ITEMS, params=params, timeout=timeout)
        response.raise_for_status()
        page = response.json()
        if matched is None:
            matched = page.get("numberMatched")
            logger.info("OAF Nutzung numberMatched=%s", matched)
        batch = page.get("features") or []
        features.extend(batch)
        if not batch or (matched is not None and len(features) >= int(matched)):
            break
        offset += len(batch)
    return {"type": "FeatureCollection", "features": features, "numberReturned": len(features)}


def load_guide_records_from_oaf(
    bbox_wgs84: Tuple[float, float, float, float],
    *,
    write_geojson: bool = False,
    output_dir: Optional[Union[str, Path]] = None,
) -> List[StreetRecord]:
    """Fetch Nutzung for ``bbox_wgs84`` and parse ``GUIDE_NUTZARTEN``.

    ``write_geojson`` is off by default. When ``True``, writes
    ``alkis_nutzung_verkehr.geojson`` and ``alkis_nutzung_weitere.geojson``
    into ``output_dir``.
    """
    data = fetch_nutzung_feature_collection(bbox_wgs84)
    if write_geojson:
        if output_dir is None:
            raise ValueError("write_geojson=True requires output_dir")
        dest = Path(output_dir)
        write_nutzung_geojson(data, dest / ALKIS_NUTZUNG_VERKEHR_GEOJSON, nutzarten=DEFAULT_NUTZARTEN)
        write_nutzung_geojson(data, dest / ALKIS_NUTZUNG_WEITERE_GEOJSON, nutzarten=WEITERE_NUTZARTEN)
    return records_from_geojson_feature_collection(data, nutzarten=GUIDE_NUTZARTEN)


__all__ = [
    "ALKIS_NUTZUNG_VERKEHR_GEOJSON",
    "ALKIS_NUTZUNG_WEITERE_GEOJSON",
    "DEFAULT_NUTZARTEN",
    "GUIDE_NUTZARTEN",
    "NUTZUNG_OAF_ITEMS",
    "WEITERE_NUTZARTEN",
    "GeometryCrs",
    "StreetRecord",
    "collect_street_psets",
    "fetch_nutzung_feature_collection",
    "load_guide_records_from_oaf",
    "load_streets_records",
    "nutzung_idebene1",
    "nutzung_split_label",
    "pset_for_nutzung_group",
    "records_from_geojson_feature_collection",
    "write_nutzung_geojson",
]
