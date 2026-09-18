"""Utilities for mapping and normalizing BoreholeML codes and attributes.

This module centralizes the lookup tables and conversion logic used by the
borehole application. It loads mapping data from the bundled JSON assets and
provides a single BoreholeMappings interface for translating BoreholeML
codes into human-readable German descriptions and display values.

Unknown or undefined values are handled consistently without failing the
conversion process. Default mapping data is loaded lazily and cached for
reuse.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from BIMFabrikHH_core.apps.boreholes.helper import (UNDEFINED,
                                                    _adjective_to_attributive,
                                                    _clean, _extract_meaning,
                                                    _split_rock_code)

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_SOIL_TYPES_FILE = "soil_type_mapping.json"
_DIN_COLORS_FILE = "din_color_mapping.json"
_ARCHIVE_ID_FILE = "archive_id_mapping.json"
_DRILLING_METHOD_FILE = "drilling_method_mapping.json"
_CHRONOSTRATIGRAPHY_FILE = "chronostratigraphy_mapping.json"
_GENESIS_FILE = "genesis_mapping.json"
_GEOGENESIS_FILE = "geogenesis_mapping.json"
_ROCK_COLORS_FILE = "rock_color_mapping.json"
_CARBONATE_CONTENT_FILE = "carbonate_content_mapping.json"
_CONSISTENCY_FILE = "consistency_mapping.json"
_COMPACTNESS_FILE = "compactness_mapping.json"


# Chronostratigraphic codes seen in the Hamburg BoreholeML service.
_STRATIGRAPHY_NAMES: dict[str, str] = {
    "qh": "Quartär holozän",
    "qp": "Quartär pleistozän",
    "q": "Quartär",
    "y": "undifferenziert",
    "t": "Tertiär",
    "k": "Kreide",
    "j": "Jura",
    "tr": "Trias",
}

Mapping = dict[str, Any]


@dataclass(frozen=True)
class BoreholeMappings:
    archive_ids: Mapping
    drilling_methods: Mapping
    carbonate_contents: Mapping
    soil_types: Mapping
    visual_colors: Mapping
    rock_colors: Mapping
    chronostratigraphies: Mapping
    genesis: Mapping
    geogenesis: Mapping
    consistencies: Mapping
    compactness: Mapping

    @classmethod
    @lru_cache(maxsize=1)
    def load_default(cls) -> "BoreholeMappings":
        return cls(
            archive_ids=cls._load_json(_ARCHIVE_ID_FILE),
            drilling_methods=cls._load_json(_DRILLING_METHOD_FILE),
            carbonate_contents=cls._load_json(_CARBONATE_CONTENT_FILE),
            soil_types=cls._load_json(_SOIL_TYPES_FILE),
            visual_colors=cls._load_json(_DIN_COLORS_FILE),
            rock_colors=cls._load_json(_ROCK_COLORS_FILE),
            chronostratigraphies=cls._load_json(_CHRONOSTRATIGRAPHY_FILE),
            genesis=cls._load_json(_GENESIS_FILE),
            geogenesis=cls._load_json(_GEOGENESIS_FILE),
            consistencies=cls._load_json(_CONSISTENCY_FILE),
            compactness=cls._load_json(_COMPACTNESS_FILE),
        )

    @staticmethod
    def _load_json(filename: str) -> dict[str, Any]:
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

    @staticmethod
    def _map_code(
        value: Any,
        mapping: Mapping[str, str],
    ) -> str:
        code = _clean(value)

        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        meaning = mapping.get(code)

        return f"{code} ({meaning})" if meaning else code

    def map_archive_id(self, borehole_id: str) -> str:
        """Map a BoreholeML ID to ``"archive_id"`` ("Archivnummer") assigned by Geologisches Landesamt Hamburg."""
        text = _clean(borehole_id)
        mapping = self.archive_ids

        return mapping.get(text, "")

    def map_drilling_method(self, value: Any) -> str:
        """Map a drilling method code to ``"code (German name)"``, e.g. ``UN (unbekanntes Bohrverfahren)``."""
        return self._map_code(value, self.drilling_methods)

    def map_carbonate(self, value: Any) -> str:
        """Map a carbonate code to ``"code (German name)"``, e.g. ``c3 (karbonathaltig)``."""
        return self._map_code(value, self.carbonate_contents)

    def map_consistency(self, value: Any) -> str:
        """Map a consistency code to ``"code (German name)"``, e.g. ``hfe (halbfest)``."""
        return self._map_code(value, self.consistencies)

    def map_compactness(self, value: Any) -> str:
        """Map a compactness code to ``"code (German name)"``, e.g. ``ld3 (mitteldicht gelagert)``."""
        return self._map_code(value, self.compactness)

    def map_genesis(self, value: Any) -> str:
        """Map a genesis code to ``"code (German name)"``, e.g. ``fl (fluviatil)``."""
        return self._map_code(value, self.genesis)

    def map_geogenesis(self, value: Any) -> str:
        """Map a geogenesis code to ``"code (German name)"``, e.g. ``yf (Auffüllung)``."""
        return self._map_code(value, self.geogenesis)

    def map_rock_color(self, value: Any) -> str:
        """Map a DIN colour code to ``"code (German name)"``, e.g. ``h8 (grau)``."""
        return self._map_code(value, self.rock_colors)

    def map_din_color(self, value: Any) -> str:
        """Map a DIN colour code to ``"code (German name)"``, e.g. ``gr (grau)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.visual_colors
        german_name = mapping.get("color_code_to_german_name", {}).get(code, "")
        return f"{code} ({german_name})" if german_name else code

    def map_chronostratigraphy(self, value: Any) -> str:
        """Map a stratigraphic code to ``"code (German name)"``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.chronostratigraphies
        german_name = (
            mapping.get(code)
            or mapping.get(code.upper())
            or mapping.get(code.lower())
            or _STRATIGRAPHY_NAMES.get(code.lower(), "")
        )
        return f"{code} ({german_name})" if german_name else code

    def map_hauptgemengteil(self, value: Any) -> str:
        """Map the main soil component, keeping compound explicit codes intact."""
        text = _clean(value)
        if not text:
            return UNDEFINED

        if "(" in text:
            text, _ = _split_rock_code(text)
            if not text:
                return UNDEFINED

        mapping = self.soil_types
        symbol = re.sub(r"\s+", "", text).strip(".,;")
        explicit_codes = mapping.get("explicit_codes", {})
        if any(c in explicit_codes for c in (symbol, symbol.capitalize(), symbol.upper(), symbol.lower())):
            return self.map_soil_symbol(text)

        if re.search(r"[,;/|]", text):
            parts = [part.strip() for part in re.split(r"[,;/|]", text) if part.strip()]
            if len(parts) > 1:
                return ", ".join(self.map_soil_symbol(part) for part in parts)

        return self.map_soil_symbol(text)

    def map_nebengemengteil(self, value: Any) -> str:
        """Map one or several secondary soil components."""
        text = _clean(value)
        if not text:
            return UNDEFINED

        if "(" in text:
            _, text = _split_rock_code(text)
            if not text:
                return UNDEFINED

        parts = [part.strip() for part in re.split(r"[,;/|]", text) if part.strip()]
        if not parts:
            return UNDEFINED
        return ", ".join(self.map_soil_symbol(part) for part in parts)

    def map_soil_symbol(self, symbol_value: Any) -> str:
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

        mapping = self.soil_types
        symbol = re.sub(r"\s+", "", text).strip(".,;")
        explicit_codes = mapping.get("explicit_codes", {})
        primary_types = mapping.get("primary_types", {})
        secondary_components = mapping.get("secondary_components", {})

        for candidate in (symbol, symbol.capitalize(), symbol.upper(), symbol.lower()):
            if candidate in explicit_codes:
                return f"{symbol} ({explicit_codes[candidate]})"

        compound_parts = re.split(r"([\-=/:])", symbol)
        if len(compound_parts) > 1:
            meaning_parts: list[str] = []
            has_any_mapped_part = False
            for part in compound_parts:
                if part in {"-", "=", "/", ":"}:
                    meaning_parts.append(part)
                    continue
                if not part:
                    continue
                part_meaning = _extract_meaning(self.map_soil_symbol(part))
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

    def visual_color_for_hauptgemengteil(self, value: Any) -> tuple[tuple[int, int, int], str]:
        """Resolve the DIN 4023 display colour from the main soil component.

        The IFC colour intentionally comes from ``hauptgemengteil``, not from the
        ``farbe`` code, which stays metadata only.

        Args:
            value: Main soil code such as ``mS``.
            color_code_mapping: Table from :func:`load_din_color_mapping`.

        Returns:
            ``((r, g, b), german_name)`` with RGB in 0-255; the table default when
            the code is unknown.
        """
        mapping = self.visual_colors
        block = mapping.get("hauptgemengteil_visual_colors", {})
        default_entry = block.get("default", {})
        default = (self._rgb_tuple(default_entry.get("rgb")), str(default_entry.get("name", "weiß")))

        by_code = block.get("by_hauptgemengteil", {})
        text = _clean(value)
        if not text or not by_code:
            return default

        key = re.sub(r"\s+", "", text)
        for candidate in (key, text):
            entry = by_code.get(candidate)
            if entry:
                return (self._rgb_tuple(entry.get("rgb")), str(entry.get("name", default[1])))

        key_lower = key.lower()
        for code, entry in by_code.items():
            if code.lower() == key_lower:
                return (self._rgb_tuple(entry.get("rgb")), str(entry.get("name", default[1])))

        return default

    @staticmethod
    def _rgb_tuple(raw: Any) -> tuple[int, int, int]:
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


__all__ = ["BoreholeMappings"]
