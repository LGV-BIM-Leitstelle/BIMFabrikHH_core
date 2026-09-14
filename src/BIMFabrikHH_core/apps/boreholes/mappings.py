"""

"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from functools import lru_cache
from pathlib import Path
import re
from typing import Any, Dict, Optional

from BIMFabrikHH_core.apps.boreholes.helper import UNDEFINED, _adjective_to_attributive, _clean

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
        )


    @staticmethod
    def _load_json(filename: str) -> Dict[str, Any]:
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


    def map_archive_id(self, borehole_id: str) -> str:
        """Map a BoreholeML ID to ``"archive_id"`` ("Archivnummer") assigned by Geologisches Landesamt Hamburg.

        Args:
            id: BoreholeML ID.
            archive_id_mapping: Table from :func:`extract_id_mapping`.

        Returns:
            ``"archive_id"``.
        """
        text = _clean(borehole_id)
        mapping = self.archive_ids

        return mapping.get(text, "")


    def map_drilling_method(self, value: Any) -> str:
        """Map a drilling method code to ``"code (German name)"``, e.g. ``UN (unbekanntes Bohrverfahren)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.drilling_methods
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_carbonate(self, value: Any) -> str:
        """Map a carbonate code to ``"code (German name)"``, e.g. ``c3 (karbonathaltig)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.carbonate_contents
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_consistency(self, value: Any) -> str:
        """Map a consistency code to ``"code (German name)"``, e.g. ``c3 (karbonathaltig)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.consistencies
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_genesis(self, value: Any) -> str:
        """Map a genesis code to ``"code (German name)"``, e.g. ``c3 (karbonathaltig)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.genesis
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_geogenesis(self, value: Any) -> str:
        """Map a geogenesis code to ``"code (German name)"``, e.g. ``c3 (karbonathaltig)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.geogenesis
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_rock_color(self, value: Any) -> str:
        """Map a DIN colour code to ``"code (German name)"``, e.g. ``h8 (grau)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.rock_colors
        german_name = mapping.get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_din_color(self, value: Any) -> str:
        """Map a DIN colour code to ``"code (German name)"``, e.g. ``gr (grau)``."""
        code = _clean(value)
        if not code or code.lower() == UNDEFINED:
            return UNDEFINED

        mapping = self.visual_colors
        german_name = mapping.get("color_code_to_german_name", {}).get(code, "")
        return f"{code} ({german_name})" if german_name else code


    def map_stratigraphy(self, value: Any) -> str:
        """Map a chronostratigraphic code to ``"code (German name)"``."""
        text = _clean(value)
        if not text or text.lower() == UNDEFINED:
            return UNDEFINED
        german_name = _STRATIGRAPHY_NAMES.get(text.lower(), "")
        return f"{text} ({german_name})" if german_name else text


    def map_chronostratigraphy(self, value: Any) -> str:
        """Map a chronostratigraphic code to ``"code (German name)"``."""
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