"""

"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from BIMFabrikHH_core.apps.boreholes.mappings import BoreholeMappings
from lxml import etree
from pydantic import BaseModel

from BIMFabrikHH_core.data_models.boreholes import BoreholeLayer, BoreholeRecord
from BIMFabrikHH_core.apps.boreholes.helper import UNDEFINED, _adjective_to_attributive, _clean, _text, _float_or_none

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
_DIN_COLORS_FILE = "din_color_mapping.json"
_ARCHIVE_ID_FILE = "archive_id_mapping.json"
_DRILLING_METHOD_FILE = "drilling_method_mapping.json"
_CHRONOSTRATIGRAPHY_FILE = "chronostratigraphy_mapping.json"
_GENESIS_FILE = "genesis_mapping.json"
_GEOGENESIS_FILE = "geogenesis_mapping.json"
_ROCK_COLORS_FILE = "rock_color_mapping.json"
_CARBONATE_CONTENT_FILE = "carbonate_content_mapping.json"
_CONSISTENCY_FILE = "consistency_mapping.json"


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


BoreholeMLSource = Union[
    etree._Element,
    etree._ElementTree,
    bytes,
    str,
    Path,
]

class BoreholeMLParser:
    def __init__(self,
                 mappings: BoreholeMappings | None = None
    ) -> None:
        self._mappings = (
            mappings if mappings is not None
            else BoreholeMappings.load_default()
        )

    # load_borehole_records
    def from_file(self, path: Union[str, Path]) -> List[BoreholeRecord]:
        """Load and parse a saved ``BoreholeML`` XML response from disk."""
        return self.parse(Path(path))


    # records_from_boreholeml
    def parse(self,
        source: BoreholeMLSource,
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
        root = self._as_root(source)
        
        # soil_types = load_soil_type_mapping()
        # visual_colors = load_din_color_mapping()
        # rock_colors = load_rock_color_mapping()
        # archive_ids = load_archive_id_mapping()
        # chronostratigraphies = load_chronostratigraphy_mapping()
        # carbonate_contents = load_carbonate_mapping()
        # genesis_dict = load_genesis_mapping()
        # geogenesis_dict = load_geogenesis_mapping()
        # consistencies = load_consistency_mapping()
        # drilling_methods = load_drilling_methods()

        records: List[BoreholeRecord] = []
        for borehole in self._iter_borehole_elements(root):
            record = self._record_from_borehole(borehole)
            if record is not None:
                records.append(record)

        logger.info(
            "Parsed %d borehole(s) with %d layer(s) from BoreholeML",
            len(records),
            sum(len(rec.layers) for rec in records),
        )

        return records



    @staticmethod
    def _iter_borehole_elements( root: etree._Element) -> List[etree._Element]:
        """Collect ``bml:Borehole`` elements from a FeatureCollection or single feature."""
        if etree.QName(root).localname == "Borehole":
            return [root]
        found = root.findall(f".//{{{BML_NS}}}Borehole")
        if not found:
            logger.warning("No bml:Borehole features found (root: %s)", etree.QName(root).localname)
        return found


    def _record_from_borehole(self, 
        borehole: etree._Element
    ) -> Optional[BoreholeRecord]:
        """Build one :class:`BoreholeRecord`; ``None`` when unusable."""
        borehole_id = _text(borehole, f"{{{BML_NS}}}id") or _clean(borehole.get(f"{{{GML_NS}}}id"))
        if not borehole_id:
            logger.warning("Skipping bml:Borehole without id")
            return None

        archive_id = self._mappings.archive_ids()

        position = self._borehole_position(borehole)
        if position is None:
            logger.warning("Borehole %s: no usable bml:location; skipped", borehole_id)
            return None
        easting, northing, ansatzhoehe_nn = position

        full_name = _text(borehole, f"{{{BML_NS}}}fullName/{{{GMD_NS}}}LocalisedCharacterString")
        short_name = _text(borehole, f"{{{BML_NS}}}shortName/{{{GMD_NS}}}LocalisedCharacterString")

        bohrvorgang_code = _text(borehole, f"{{{BML_NS}}}drillingMethod")
        bohrvorgang_text = self._mappings.map_drilling_method(bohrvorgang_code)

        record = BoreholeRecord(
            borehole_id=borehole_id,
            archive_id=archive_id,
            aufschlussbezeichnung=full_name or short_name or borehole_id,
            easting=easting,
            northing=northing,
            ansatzhoehe_nn=ansatzhoehe_nn,
            endteufe=self._float_or_none(_text(borehole, f"{{{BML_NS}}}totalLength")),
            bohrdatum=_text(borehole, f"{{{BML_NS}}}drillingDate"),
            bohrvorgang=bohrvorgang_text,
            projekt=_text(borehole, f"{{{BML_NS}}}project"),
        )

        series = self._latest_interval_series(borehole)
        intervals = series.findall(f"{{{BML_NS}}}layer/{{{BML_NS}}}Interval") if series is not None else []
        layers: List[BoreholeLayer] = []
        for index, interval in enumerate(intervals, start=1):
            layer = self._layer_from_interval(
                interval,
                borehole_id=borehole_id,
                index=index,
                ansatzhoehe_nn=ansatzhoehe_nn,
                soil_types=soil_types,
                visual_colors=visual_colors,
                rock_colors=rock_colors,
                chronostratigraphies=chronostratigraphies,
                carbonate_contents=carbonate_contents,
                genesis_dict=genesis_dict,
                geogenesis_dict=geogenesis_dict,
                consistencies=consistencies,
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
            Pset_Hyperlink.pset_name: self.build_borehole_hyperlink(
                record.archive_id,
                record.aufschlussbezeichnung,
            ),
        }
        for layer in record.layers:
            bereich = layer.psets.get(Pset_Aufschlussbereich.pset_name)
            if isinstance(bereich, Pset_Aufschlussbereich):
                bereich.bohrvorgang = record.bohrvorgang or UNDEFINED
        return record


    def _layer_from_interval(self,
        interval: etree._Element,
        *,
        borehole_id: str,
        index: int,
        ansatzhoehe_nn: float,
    ) -> Optional[BoreholeLayer]:
        """Build one :class:`BoreholeLayer`; ``None`` when depths are unusable."""
        from_depth = self._float_or_none(_text(interval, f"{{{BML_NS}}}from"))
        to_depth = self._float_or_none(_text(interval, f"{{{BML_NS}}}to"))
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

        hauptgemengteil, nebengemengteil, rock_color = _lithology_components(interval)
        genese = _text(interval, f"{{{BML_NS}}}genesis")
        geogenese = _text(interval, f"{{{BML_NS}}}geoGenesis")
        visual_rgb, din_color_name = visual_color_for_hauptgemengteil(hauptgemengteil, visual_colors)

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
            geogenese=geogenese,
            farbe=rock_color,
            kalkgehalt=_text(interval, f"{{{BML_NS}}}carbonateContent"),
            konsistenz=_text(interval, f"{{{BML_NS}}}consistency"),
            visual_rgb=visual_rgb,
            din_color_name=din_color_name,
        )
        layer.psets = self._layer_psets(layer)
        return layer


    def _layer_psets(self, layer: BoreholeLayer) -> Dict[str, BaseModel]:
        """Build the layer-level pset templates with DIN texts resolved."""
        aufschlussbereich = Pset_Aufschlussbereich(
            bodenart=self._mappings.map_hauptgemengteil(layer.hauptgemengteil),
            bodenart_ergaenzung=self._mappings.map_nebengemengteil(layer.nebengemengteil),
            farbe=self._mappings.map_rock_color(layer.farbe),
            kalkgehalt=self._mappings.map_carbonate(layer.kalkgehalt),
            stratigrafie=self._mappings.map_chronostratigraphy(layer.stratigraphie),
        )
        schicht = Pset_Schicht(
            genese=self._mappings.map_genesis(layer.genese),
            geogenese=self._mappings.map_geogenesis(layer.geogenese),
            bodenkonsistenz=self._mappings.map_consistency(layer.konsistenz),
            geologische_bezeichnung=layer.rock_name_text or UNDEFINED,
        )
        objektinformation = Pset_Objektinformation_Borehole()

        return {
            Pset_Aufschlussbereich.pset_name: aufschlussbereich,
            Pset_Schicht.pset_name: schicht,
            Pset_Objektinformation_Borehole.pset_name: objektinformation,
        }