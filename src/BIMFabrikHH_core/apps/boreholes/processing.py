"""Borehole data pipeline: WFS ``BoreholeML 3.0`` XML → :class:`BoreholeRecord`.

Pure processing only — no HTTP and no IFC. The caller fetches the WFS
response (the API does this in ``DataFetcher.fetch_borehole_data``) and hands
the parsed XML, raw bytes or a saved file to
:func:`records_from_boreholeml` / :func:`load_borehole_records`.

Soil and colour codes are resolved with the DIN 4023 / DIN EN ISO 14688-1
tables in this app's ``assets`` folder (``soil_type_mapping.json`` and
``color_code_mapping.json``).
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree
from pydantic import BaseModel

from BIMFabrikHH_core.data_models.boreholes import BoreholeLayer, BoreholeRecord
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_boreholes import (
    Pset_Aufschluss,
    Pset_Aufschlussbereich,
    Pset_Objektinformation_Borehole,
    Pset_Schicht,
)

logger = logging.getLogger(__name__)

BML_NS = "http://www.infogeo.de/boreholeml/3.0"
GML_NS = "http://www.opengis.net/gml/3.2"
WFS_NS = "http://www.opengis.net/wfs/2.0"
GMD_NS = "http://www.isotc211.org/2005/gmd"

UNDEFINED = "undefiniert"

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_SOIL_TYPES_FILE = "soil_type_mapping.json"
_COLORS_FILE = "color_code_mapping.json"

# Borehole viewer of the Hamburg geodienste portal. ``sid`` identifies the
# area and is constant for the tested extent (carried over from the intern
# app, which has the same open TODO for an area → sid mapping).
BOREHOLE_PORTAL_URL = "https://geodienste.hamburg.de/app/render"
BOREHOLE_PORTAL_SID = "0x960470caL0x71973d4cL"

# Chronostratigraphic codes seen in the Hamburg BoreholeML service.
_STRATIGRAPHY_NAMES: Dict[str, str] = {
    "qh": "Quartär holozän",
    "qp": "Quartär pleistozän",
    "q": "Quartär",
    "y": "undifferenziert",
    "t": "Tertiär",
    "k": "Kreide",
    "j": "Jura",
    "tr": "Trias",
}


# ---------------------------------------------------------------------------
# Mapping tables
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def load_soil_type_mapping() -> Dict[str, Any]:
    """Load the DIN soil symbol table; empty dict when the file is missing."""
    return _load_config_json(_SOIL_TYPES_FILE)


@lru_cache(maxsize=1)
def load_color_code_mapping() -> Dict[str, Any]:
    """Load the DIN colour table; empty dict when the file is missing."""
    return _load_config_json(_COLORS_FILE)


def _load_config_json(filename: str) -> Dict[str, Any]:
    path = ASSETS_DIR / filename
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Borehole mapping file missing: %s", path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Borehole mapping file %s could not be read: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _adjective_to_attributive(adjective: str) -> str:
    """``schluffig`` → ``schluffiger`` for combined soil names."""
    value = adjective.strip().lower()
    if value.endswith("ig") or value.endswith("isch"):
        return f"{adjective}er"
    return adjective


def _extract_meaning(mapped_symbol: str) -> Optional[str]:
    """Pull ``Meaning`` out of a ``Code (Meaning)`` string."""
    match = re.fullmatch(r".+\s\((.+)\)", mapped_symbol)
    return match.group(1) if match else None


def map_soil_symbol(symbol_value: Any, soil_type_mapping: Optional[Dict[str, Any]] = None) -> str:
    """Map a DIN EN ISO 14688-1 soil symbol to ``"code (German meaning)"``.

    Explicit codes win (``mS`` → ``Mittelsand``), then compound notation
    (``fS-mS``), then primary/secondary tables, then the combinatoric forms
    ``uS`` (schluffiger Sand) and ``gS`` (grobsand).

    Args:
        symbol_value: Raw soil code from BoreholeML ``rockName``.
        soil_type_mapping: Table from :func:`load_soil_type_mapping`.

    Returns:
        ``"code (meaning)"``, the bare code when unknown, or ``"undefiniert"``.
    """
    text = _clean(symbol_value)
    if not text:
        return UNDEFINED

    mapping = soil_type_mapping if soil_type_mapping is not None else load_soil_type_mapping()
    symbol = re.sub(r"\s+", "", text).strip(".,;")
    explicit_codes = mapping.get("explicit_codes", {})
    primary_types = mapping.get("primary_types", {})
    secondary_components = mapping.get("secondary_components", {})

    for candidate in (symbol, symbol.capitalize(), symbol.upper(), symbol.lower()):
        if candidate in explicit_codes:
            return f"{symbol} ({explicit_codes[candidate]})"

    compound_parts = re.split(r"([\-=/:])", symbol)
    if len(compound_parts) > 1:
        meaning_parts: List[str] = []
        has_any_mapped_part = False
        for part in compound_parts:
            if part in {"-", "=", "/", ":"}:
                meaning_parts.append(part)
                continue
            if not part:
                continue
            part_meaning = _extract_meaning(map_soil_symbol(part, mapping))
            if part_meaning is None:
                meaning_parts.append(part)
            else:
                has_any_mapped_part = True
                meaning_parts.append(part_meaning)
        if has_any_mapped_part:
            return f"{symbol} ({''.join(meaning_parts)})"

    if symbol in primary_types:
        return f"{symbol} ({primary_types[symbol]})"
    if symbol in secondary_components:
        return f"{symbol} ({secondary_components[symbol]})"

    combined = re.fullmatch(r"([a-z]{1,2})([A-Z])", symbol)
    if combined:
        secondary_code, primary_code = combined.groups()
        if secondary_code in secondary_components and primary_code in primary_types:
            secondary_name = _adjective_to_attributive(secondary_components[secondary_code])
            return f"{symbol} ({secondary_name} {primary_types[primary_code]})"

    prefixed = re.fullmatch(r"([gmf])([GSUT])", symbol)
    if prefixed:
        prefix, base_symbol = prefixed.groups()
        base_name = primary_types.get(base_symbol)
        prefix_name = mapping.get("grain_size_prefixes", {}).get(prefix)
        if base_name and prefix_name:
            return f"{symbol} ({prefix_name}{base_name.lower()})"

    return symbol


def map_hauptgemengteil(value: Any, soil_type_mapping: Optional[Dict[str, Any]] = None) -> str:
    """Map the main soil component, keeping compound explicit codes intact."""
    text = _clean(value)
    if not text:
        return UNDEFINED

    mapping = soil_type_mapping if soil_type_mapping is not None else load_soil_type_mapping()
    symbol = re.sub(r"\s+", "", text).strip(".,;")
    explicit_codes = mapping.get("explicit_codes", {})
    if any(c in explicit_codes for c in (symbol, symbol.capitalize(), symbol.upper(), symbol.lower())):
        return map_soil_symbol(text, mapping)

    if re.search(r"[,;/|]", text):
        parts = [part.strip() for part in re.split(r"[,;/|]", text) if part.strip()]
        if len(parts) > 1:
            return ", ".join(map_soil_symbol(part, mapping) for part in parts)

    return map_soil_symbol(text, mapping)


def map_nebengemengteil(value: Any, soil_type_mapping: Optional[Dict[str, Any]] = None) -> str:
    """Map one or several secondary soil components."""
    text = _clean(value)
    if not text:
        return UNDEFINED

    mapping = soil_type_mapping if soil_type_mapping is not None else load_soil_type_mapping()
    parts = [part.strip() for part in re.split(r"[,;/|]", text) if part.strip()]
    if not parts:
        return UNDEFINED
    return ", ".join(map_soil_symbol(part, mapping) for part in parts)


def map_color_code(value: Any, color_code_mapping: Optional[Dict[str, Any]] = None) -> str:
    """Map a DIN colour code to ``"code (German name)"``, e.g. ``gr (grau)``."""
    text = _clean(value)
    if not text or text.lower() == UNDEFINED:
        return UNDEFINED

    mapping = color_code_mapping if color_code_mapping is not None else load_color_code_mapping()
    german_name = mapping.get("color_code_to_german_name", {}).get(text, "")
    return f"{text} ({german_name})" if german_name else text


def map_stratigraphy(value: Any) -> str:
    """Map a chronostratigraphic code to ``"code (German name)"``."""
    text = _clean(value)
    if not text or text.lower() == UNDEFINED:
        return UNDEFINED
    german_name = _STRATIGRAPHY_NAMES.get(text.lower(), "")
    return f"{text} ({german_name})" if german_name else text


def visual_color_for_hauptgemengteil(
    value: Any,
    color_code_mapping: Optional[Dict[str, Any]] = None,
) -> Tuple[Tuple[int, int, int], str]:
    """Resolve the DIN 4023 display colour from the main soil component.

    The IFC colour intentionally comes from ``hauptgemengteil``, not from the
    ``farbe`` code, which stays metadata only.

    Args:
        value: Main soil code such as ``mS``.
        color_code_mapping: Table from :func:`load_color_code_mapping`.

    Returns:
        ``((r, g, b), german_name)`` with RGB in 0-255; the table default when
        the code is unknown.
    """
    mapping = color_code_mapping if color_code_mapping is not None else load_color_code_mapping()
    block = mapping.get("hauptgemengteil_visual_colors", {})
    default_entry = block.get("default", {})
    default = (_rgb_tuple(default_entry.get("rgb")), str(default_entry.get("name", "weiß")))

    by_code = block.get("by_hauptgemengteil", {})
    text = _clean(value)
    if not text or not by_code:
        return default

    key = re.sub(r"\s+", "", text)
    for candidate in (key, text):
        entry = by_code.get(candidate)
        if entry:
            return (_rgb_tuple(entry.get("rgb")), str(entry.get("name", default[1])))

    key_lower = key.lower()
    for code, entry in by_code.items():
        if code.lower() == key_lower:
            return (_rgb_tuple(entry.get("rgb")), str(entry.get("name", default[1])))

    return default


def build_borehole_hyperlink(
    borehole_id: str,
    aufschlussbezeichnung: str = "",
    *,
    portal_id: Optional[str] = None,
) -> Pset_Hyperlink:
    """Build the geodienste borehole-viewer link, as in the intern app.

    The URL is the fixed ``{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}``
    part plus the borehole id.

    Note:
        The portal expects the numeric Archivnummer that the intern app read
        from its SQLite ``id_stammdaten`` column. BoreholeML only publishes
        the textual ``bml:id`` (e.g. ``BDHH_6434B1``), which the portal
        rejects, so pass ``portal_id`` once that number is available from
        another source.

    Args:
        borehole_id: ``bml:id`` of the borehole, used as ``id`` by default.
        aufschlussbezeichnung: Designation for the remark text.
        portal_id: Explicit ``id`` query value, overriding ``borehole_id``.

    Returns:
        ``Pset_Hyperlink`` with the URL and a German remark.
    """
    link_id = portal_id or borehole_id
    url = f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id={link_id}"
    if aufschlussbezeichnung:
        bemerkung = f"Link zur Bohrung {aufschlussbezeichnung} (ID: {link_id})"
    else:
        bemerkung = f"Link zur Bohrung (ID: {link_id})"
    return Pset_Hyperlink(hyperlink_001=url, hyperlink_001_bemerkung=bemerkung)


def _rgb_tuple(raw: Any) -> Tuple[int, int, int]:
    """Coerce a JSON ``[r, g, b]`` entry into a 0-255 int triple."""
    if isinstance(raw, (list, tuple)) and len(raw) == 3:
        try:
            values = [float(v) for v in raw]
        except (TypeError, ValueError):
            return (254, 254, 254)
        if all(v <= 1.0 for v in values):
            values = [v * 255.0 for v in values]
        return tuple(max(0, min(255, int(round(v)))) for v in values)  # type: ignore[return-value]
    return (254, 254, 254)


# ---------------------------------------------------------------------------
# BoreholeML parsing
# ---------------------------------------------------------------------------


def _clean(value: Any) -> str:
    """Trimmed string for XML text / attribute values (``None`` → ``""``)."""
    if value is None:
        return ""
    return str(value).strip()


def _text(element: Optional[etree._Element], path: str) -> str:
    """Trimmed text of the first ``path`` match below ``element``."""
    if element is None:
        return ""
    return _clean(element.findtext(path))


def _float_or_none(value: Any) -> Optional[float]:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _as_root(source: Union[etree._Element, etree._ElementTree, bytes, str, Path]) -> etree._Element:
    """Normalize the accepted input types to a single XML root element."""
    if isinstance(source, etree._ElementTree):
        return source.getroot()
    if isinstance(source, etree._Element):
        return source
    if isinstance(source, Path):
        return etree.parse(str(source)).getroot()
    if isinstance(source, bytes):
        return etree.fromstring(source)
    if isinstance(source, str):
        return etree.fromstring(source.encode("utf-8"))
    raise TypeError(f"Unsupported BoreholeML source type: {type(source).__name__}")


def _iter_borehole_elements(root: etree._Element) -> List[etree._Element]:
    """Collect ``bml:Borehole`` elements from a FeatureCollection or single feature."""
    if etree.QName(root).localname == "Borehole":
        return [root]
    found = root.findall(f".//{{{BML_NS}}}Borehole")
    if not found:
        logger.warning("No bml:Borehole features found (root: %s)", etree.QName(root).localname)
    return found


def _borehole_position(borehole: etree._Element) -> Optional[Tuple[float, float, float]]:
    """Read ``bml:location`` as ``(easting, northing, height)`` in EPSG:25832/NHN.

    The service default CRS is ``EPSG:5555``, the *compound* CRS ETRS89 /
    UTM 32N + DHHN height. Its horizontal part is exactly EPSG:25832, so
    easting and northing are already the map metres the IFC georeferencing
    context expects, and no transformation is needed.

    ``EPSG:25832`` and ``EPSG:4326`` are advertised as ``OtherCRS``, but both
    are two-dimensional: requesting them makes the service emit a 2D
    ``gml:pos`` and drop the Ansatzhöhe that the layer stacking depends on.
    ``EPSG:5555`` is therefore the only CRS that yields position and height in
    one request. Height still falls back to ``bml:origin`` when absent.
    """
    pos = _text(borehole, f"{{{BML_NS}}}location/{{{GML_NS}}}Point/{{{GML_NS}}}pos")
    parts = [p for p in pos.split() if p]
    if len(parts) < 2:
        return None
    easting = _float_or_none(parts[0])
    northing = _float_or_none(parts[1])
    if easting is None or northing is None:
        return None

    height = _float_or_none(parts[2]) if len(parts) > 2 else None
    if height is None:
        height = _float_or_none(_text(borehole, f"{{{BML_NS}}}origin/{{{BML_NS}}}Origin/{{{BML_NS}}}elevation"))
    return (easting, northing, height if height is not None else 0.0)


def _latest_interval_series(borehole: etree._Element) -> Optional[etree._Element]:
    """Pick the ``IntervalSeries`` with the highest ``version`` (latest reading)."""
    series = borehole.findall(f"{{{BML_NS}}}intervalSeries/{{{BML_NS}}}IntervalSeries")
    if not series:
        return None
    if len(series) == 1:
        return series[0]

    def version_of(node: etree._Element) -> float:
        return _float_or_none(_text(node, f"{{{BML_NS}}}version")) or 0.0

    latest = max(series, key=version_of)
    logger.debug(
        "Borehole has %d interval series; using version %s",
        len(series),
        _text(latest, f"{{{BML_NS}}}version"),
    )
    return latest


def _split_rock_code(rock_code: str) -> Tuple[str, str]:
    """Split a DIN ``rockCode`` into main and secondary components.

    Two notations occur in the Hamburg service: ``F(s4, hz4, ht2)`` puts the
    secondary components in brackets, ``mS, yy`` lists co-equal components.

    Args:
        rock_code: Raw ``bml:rockCode`` value.

    Returns:
        ``(hauptgemengteil, nebengemengteil)``; both may be empty.
    """
    text = _clean(rock_code)
    if not text:
        return ("", "")

    bracket = re.match(r"^([^(]+)\((.*)\)\s*$", text)
    if bracket:
        return (bracket.group(1).strip(), bracket.group(2).strip())

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return ("", "")
    return (parts[0], ", ".join(parts[1:]))


def _lithology_components(interval: etree._Element) -> Tuple[str, str, str]:
    """Resolve the soil components and colour of one ``bml:Interval``.

    ``bml:rockCode`` is preferred because the dominant component often has no
    ``RockNameList`` entry and therefore an empty ``rockName`` (e.g. ``F`` for
    Mudde at 64 %), which would otherwise promote a minor component. The
    ``bml:lithology`` blocks are the fallback, sorted by ``percentage``.

    Returns:
        ``(hauptgemengteil, nebengemengteil, farbe)``.
    """
    color = ""
    entries: List[Tuple[float, str]] = []
    for lithology in interval.findall(f"{{{BML_NS}}}lithology/{{{BML_NS}}}Lithology"):
        if not color:
            color = _text(lithology, f"{{{BML_NS}}}rockColor")
        rock_name = _text(lithology, f"{{{BML_NS}}}rockName")
        if rock_name:
            percentage = _float_or_none(_text(lithology, f"{{{BML_NS}}}percentage")) or 0.0
            entries.append((percentage, rock_name))

    haupt, neben = _split_rock_code(_text(interval, f"{{{BML_NS}}}rockCode"))
    if haupt:
        return (haupt, neben, color)

    entries.sort(key=lambda item: item[0], reverse=True)
    codes = [name for _, name in entries]
    if not codes:
        return ("", "", color)
    return (codes[0], ", ".join(codes[1:]), color)


def _layer_from_interval(
    interval: etree._Element,
    *,
    borehole_id: str,
    index: int,
    ansatzhoehe_nn: float,
    soil_types: Dict[str, Any],
    colors: Dict[str, Any],
) -> Optional[BoreholeLayer]:
    """Build one :class:`BoreholeLayer`; ``None`` when depths are unusable."""
    from_depth = _float_or_none(_text(interval, f"{{{BML_NS}}}from"))
    to_depth = _float_or_none(_text(interval, f"{{{BML_NS}}}to"))
    if from_depth is None or to_depth is None:
        logger.warning("Borehole %s layer %d: missing from/to depth; skipped", borehole_id, index)
        return None

    upper_height = ansatzhoehe_nn - from_depth
    lower_height = ansatzhoehe_nn - to_depth
    thickness = abs(upper_height - lower_height)
    if thickness <= 0.0:
        logger.warning(
            "Borehole %s layer %d: zero thickness (%.3f–%.3f m); skipped",
            borehole_id,
            index,
            from_depth,
            to_depth,
        )
        return None

    hauptgemengteil, nebengemengteil, color = _lithology_components(interval)
    genese = _text(interval, f"{{{BML_NS}}}geoGenesis") or _text(interval, f"{{{BML_NS}}}genesis")
    visual_rgb, din_color_name = visual_color_for_hauptgemengteil(hauptgemengteil, colors)

    layer = BoreholeLayer(
        layer_id=f"{borehole_id}_{index}",
        from_depth=from_depth,
        to_depth=to_depth,
        upper_height=upper_height,
        lower_height=lower_height,
        thickness=thickness,
        hauptgemengteil=hauptgemengteil,
        nebengemengteil=nebengemengteil,
        rock_name_text=_text(interval, f"{{{BML_NS}}}rockNameText/{{{GMD_NS}}}LocalisedCharacterString"),
        stratigraphie=_text(
            interval,
            f"{{{BML_NS}}}stratigraphy/{{{BML_NS}}}Stratigraphy/{{{BML_NS}}}chronoStratigraphy",
        ),
        genese=genese,
        farbe=color,
        kalkgehalt=_text(interval, f"{{{BML_NS}}}carbonateContent"),
        konsistenz=_text(interval, f"{{{BML_NS}}}consistency"),
        visual_rgb=visual_rgb,
        din_color_name=din_color_name,
    )
    layer.psets = _layer_psets(layer, soil_types=soil_types, colors=colors)
    return layer


def _layer_psets(
    layer: BoreholeLayer,
    *,
    soil_types: Dict[str, Any],
    colors: Dict[str, Any],
) -> Dict[str, BaseModel]:
    """Build the layer-level pset templates with DIN texts resolved."""
    aufschlussbereich = Pset_Aufschlussbereich(
        bodenart=map_hauptgemengteil(layer.hauptgemengteil, soil_types),
        bodenart_ergaenzung=map_nebengemengteil(layer.nebengemengteil, soil_types),
        farbe=map_color_code(layer.farbe, colors),
        kalkgehalt=layer.kalkgehalt or UNDEFINED,
        stratigrapfie=map_stratigraphy(layer.stratigraphie),
    )
    schicht = Pset_Schicht(
        genese=layer.genese or UNDEFINED,
        bodenkonsistenz=layer.konsistenz or UNDEFINED,
        geologische_bezeichnung=layer.rock_name_text or UNDEFINED,
    )
    objektinformation = Pset_Objektinformation_Borehole()
    return {
        Pset_Aufschlussbereich.pset_name: aufschlussbereich,
        Pset_Schicht.pset_name: schicht,
        Pset_Objektinformation_Borehole.pset_name: objektinformation,
    }


def _record_from_borehole(
    borehole: etree._Element,
    *,
    soil_types: Dict[str, Any],
    colors: Dict[str, Any],
) -> Optional[BoreholeRecord]:
    """Build one :class:`BoreholeRecord`; ``None`` when unusable."""
    borehole_id = _text(borehole, f"{{{BML_NS}}}id") or _clean(borehole.get(f"{{{GML_NS}}}id"))
    if not borehole_id:
        logger.warning("Skipping bml:Borehole without id")
        return None

    position = _borehole_position(borehole)
    if position is None:
        logger.warning("Borehole %s: no usable bml:location; skipped", borehole_id)
        return None
    easting, northing, ansatzhoehe_nn = position

    full_name = _text(borehole, f"{{{BML_NS}}}fullName/{{{GMD_NS}}}LocalisedCharacterString")
    short_name = _text(borehole, f"{{{BML_NS}}}shortName/{{{GMD_NS}}}LocalisedCharacterString")

    record = BoreholeRecord(
        borehole_id=borehole_id,
        aufschlussbezeichnung=full_name or short_name or borehole_id,
        easting=easting,
        northing=northing,
        ansatzhoehe_nn=ansatzhoehe_nn,
        endteufe=_float_or_none(_text(borehole, f"{{{BML_NS}}}totalLength")),
        bohrdatum=_text(borehole, f"{{{BML_NS}}}drillingDate"),
        bohrvorgang=_text(borehole, f"{{{BML_NS}}}drillingMethod"),
        projekt=_text(borehole, f"{{{BML_NS}}}project"),
    )

    series = _latest_interval_series(borehole)
    intervals = series.findall(f"{{{BML_NS}}}layer/{{{BML_NS}}}Interval") if series is not None else []
    layers: List[BoreholeLayer] = []
    for index, interval in enumerate(intervals, start=1):
        layer = _layer_from_interval(
            interval,
            borehole_id=borehole_id,
            index=index,
            ansatzhoehe_nn=ansatzhoehe_nn,
            soil_types=soil_types,
            colors=colors,
        )
        if layer is not None:
            layers.append(layer)

    if not layers:
        logger.warning("Borehole %s: no usable layers; skipped", borehole_id)
        return None

    record.layers = sorted(layers, key=lambda item: item.upper_height, reverse=True)
    record.psets = {
        Pset_Aufschluss.pset_name: Pset_Aufschluss(
            aufschlussart="Bohrung",
            aufschlussdatum=record.bohrdatum or UNDEFINED,
            aufschlussnummer=record.aufschlussbezeichnung,
            hoehenansatzpunkt=record.ansatzhoehe_nn,
            laenge_baugrundaufschluss=record.endteufe,
        ),
        Pset_Hyperlink.pset_name: build_borehole_hyperlink(
            record.borehole_id,
            record.aufschlussbezeichnung,
        ),
    }
    for layer in record.layers:
        bereich = layer.psets.get(Pset_Aufschlussbereich.pset_name)
        if isinstance(bereich, Pset_Aufschlussbereich):
            bereich.bohrvorgang = record.bohrvorgang or UNDEFINED
    return record


def records_from_boreholeml(
    source: Union[etree._Element, etree._ElementTree, bytes, str, Path],
) -> List[BoreholeRecord]:
    """Parse a WFS ``BoreholeML 3.0`` response into borehole records.

    Args:
        source: ``bml:Borehole`` element, a ``wfs:FeatureCollection`` root, an
            ``ElementTree``, or the raw XML as ``bytes`` / ``str``. The API
            passes the element returned by ``WFSAPI.fetch_data`` straight in.

    Returns:
        One record per usable borehole, layers ordered top-down. Features
        without id, location or layers are logged and skipped.
    """
    root = _as_root(source)
    soil_types = load_soil_type_mapping()
    colors = load_color_code_mapping()

    records: List[BoreholeRecord] = []
    for borehole in _iter_borehole_elements(root):
        record = _record_from_borehole(borehole, soil_types=soil_types, colors=colors)
        if record is not None:
            records.append(record)

    logger.info(
        "Parsed %d borehole(s) with %d layer(s) from BoreholeML",
        len(records),
        sum(len(rec.layers) for rec in records),
    )
    return records


def load_borehole_records(path: Union[str, Path]) -> List[BoreholeRecord]:
    """Load and parse a saved ``BoreholeML`` XML response from disk."""
    return records_from_boreholeml(Path(path))


__all__ = [
    "BOREHOLE_PORTAL_SID",
    "BOREHOLE_PORTAL_URL",
    "build_borehole_hyperlink",
    "load_borehole_records",
    "load_color_code_mapping",
    "load_soil_type_mapping",
    "map_color_code",
    "map_hauptgemengteil",
    "map_nebengemengteil",
    "map_soil_symbol",
    "map_stratigraphy",
    "records_from_boreholeml",
    "visual_color_for_hauptgemengteil",
]
