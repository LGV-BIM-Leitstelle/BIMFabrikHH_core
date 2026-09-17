"""Borehole data pipeline: WFS ``BoreholeML 3.0`` XML → :class:`BoreholeRecord`.

Pure processing only — no HTTP and no IFC. The caller fetches the WFS
response (the API does this in ``DataFetcher.fetch_borehole_data``) and hands
the parsed XML, raw bytes or a saved file to
:func:`parse` / :func:`from_file`.

Soil, colour and other codes are resolved with the tables in this app's 
``assets`` folder (``soil_type_mapping.json`` and
``din_color_mapping.json``).
"""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree
from pydantic import BaseModel

from BIMFabrikHH_core.data_models.boreholes import BoreholeLayer, BoreholeRecord, BoreholeWater
from .mappings import BoreholeMappings
from .helper import UNDEFINED, _clean, _text, _float_or_none, _split_rock_code

from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_boreholes import (
    Pset_Objektinformation_Borehole,
    Pset_Aufschluss_Borehole,
    Pset_Aufschlussbereich_Borehole,
    Pset_Schicht_Borehole,
)
from BIMFabrikHH_core.data_models.pydantic_psets_groundwater import (
    Pset_Objektinformation_Water,
    Pset_Schicht_Water,
    Pset_Wasser_Water
)


logger = logging.getLogger(__name__)

BML_NS = "http://www.infogeo.de/boreholeml/3.0"
GML_NS = "http://www.opengis.net/gml/3.2"
WFS_NS = "http://www.opengis.net/wfs/2.0"
GMD_NS = "http://www.isotc211.org/2005/gmd"


# Borehole viewer of the Hamburg geodienste portal. ``sid`` identifies the
# area and is constant for the tested extent (carried over from the intern
# app, which has the same open TODO for an area → sid mapping).
BOREHOLE_PORTAL_URL = "https://geodienste.hamburg.de/app/render"
BOREHOLE_PORTAL_SID = "0x960470caL0x71973d4cL"

XMLSource = (
    etree._Element
    | etree._ElementTree
    | bytes
    | str
    | Path
)

class BoreholeMLProcessor:
    def __init__(
            self,
            mappings: BoreholeMappings | None = None
    ) -> None:
        self._mappings = (
            mappings if mappings is not None
            else BoreholeMappings.load_default()
        )


    def from_file(self, path: str | Path) -> list[BoreholeRecord]:
        """Load and parse a saved ``BoreholeML`` XML response from disk."""
        return self.parse(Path(path))


    def parse(self,
        source: XMLSource,
    ) -> list[BoreholeRecord]:
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

        records: list[BoreholeRecord] = []
        for borehole in self._collect_boreholes(root):
            record = self._parse_borehole(borehole)
            if record is not None:
                records.append(record)

        logger.info(
            "Parsed %d borehole(s) with %d layer(s) from BoreholeML",
            len(records),
            sum(len(rec.layers) for rec in records),
        )

        return records


    @staticmethod
    def _as_root(source: XMLSource) -> etree._Element:
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


    @staticmethod
    def _collect_boreholes( root: etree._Element) -> list[etree._Element]:
        """Collect ``bml:Borehole`` elements from a FeatureCollection or single feature."""
        if etree.QName(root).localname == "Borehole":
            return [root]
        found = root.findall(f".//{{{BML_NS}}}Borehole")
        if not found:
            logger.warning("No bml:Borehole features found (root: %s)", etree.QName(root).localname)
        return found

            
    def _parse_borehole(self, 
        borehole: etree._Element
    ) -> BoreholeRecord | None:
        """Build one :class:`BoreholeRecord`; ``None`` when unusable."""
        borehole_id = _text(borehole, f"{{{BML_NS}}}id") or _clean(borehole.get(f"{{{GML_NS}}}id"))
        if not borehole_id:
            logger.warning("Skipping bml:Borehole without id")
            return None

        archive_id = self._mappings.map_archive_id(borehole_id)

        position = self._parse_borehole_position(borehole)
        if position is None:
            logger.warning("Borehole %s: no usable bml:location; skipped", borehole_id)
            return None
        easting, northing, ansatzhoehe_nn = position

        water = self._parse_groundwater(borehole, borehole_id)

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
            endteufe=_float_or_none(_text(borehole, f"{{{BML_NS}}}totalLength")),
            bohrdatum=_text(borehole, f"{{{BML_NS}}}drillingDate"),
            bohrvorgang=bohrvorgang_text,
            projekt=_text(borehole, f"{{{BML_NS}}}project"),
            groundwater=water,
        )

        interval_series = self._find_latest_interval_series(borehole)
        record.layers = self._parse_layers(interval_series, borehole_id, ansatzhoehe_nn)

        if not record.layers:
            logger.warning("Borehole %s: no usable layers; skipped", borehole_id)
            return None
        
        record.psets = {
            Pset_Aufschluss_Borehole.pset_name: Pset_Aufschluss_Borehole(
                aufschlussart="Bohrung",
                aufschlussdatum=record.bohrdatum or UNDEFINED,
                aufschlussnummer=record.aufschlussbezeichnung,
                hoehenansatzpunkt=record.ansatzhoehe_nn,
                laenge_baugrundaufschluss=record.endteufe,
            ),
            Pset_Hyperlink.pset_name: self._build_borehole_hyperlink(
                record.archive_id,
                record.aufschlussbezeichnung
            ),
        }
        for layer in record.layers:
            bereich = layer.psets.get(Pset_Aufschlussbereich_Borehole.pset_name)
            if isinstance(bereich, Pset_Aufschlussbereich_Borehole):
                bereich.bohrvorgang = record.bohrvorgang or UNDEFINED
        return record


    def _parse_layers(self, series: etree._Element, borehole_id: str, ansatzhoehe_nn: float) -> list[BoreholeLayer]:
        intervals = series.findall(f"{{{BML_NS}}}layer/{{{BML_NS}}}Interval") if series is not None else []
        layers: list[BoreholeLayer] = []
        for index, interval in enumerate(intervals, start=1):
            layer = self._parse_single_layer(
                interval,
                borehole_id=borehole_id,
                index=index,
                ansatzhoehe_nn=ansatzhoehe_nn
            )
            if layer is not None:
                layers.append(layer)

        if not layers:
            return None

        return sorted(layers, key=lambda item: item.upper_height, reverse=True)


    @staticmethod
    def _parse_borehole_position(borehole: etree._Element) -> tuple[float, float, float] | None:
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





    @staticmethod
    def _build_borehole_hyperlink(archive_id: int | str, aufschlussbezeichnung: str = "") -> Pset_Hyperlink:
        """Build the geodienste borehole-viewer link, as in the intern app.

        The URL is the fixed ``{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}``
        part plus the borehole archive id.

        Note:
            The portal expects the numeric Archivnummer (e.g. ``50300``)
            assigned by Geologisches Landesamt Hamburg, not the textual ``bml:id``
            (e.g. ``BDHH_6434B1``), which the portal rejects.
        Args:
            archive_id: Explicit ``id`` query value.
            aufschlussbezeichnung: Designation for the remark text.
            

        Returns:
            ``Pset_Hyperlink`` with the URL and a German remark.
        """
        link_id = str(archive_id)
        url = f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id={link_id}"
        if aufschlussbezeichnung:
            bemerkung = f"Link zur Bohrung {aufschlussbezeichnung} (ID: {link_id})"
        else:
            bemerkung = f"Link zur Bohrung (ID: {link_id})"
        return Pset_Hyperlink(hyperlink_001=url, hyperlink_001_bemerkung=bemerkung)


    @staticmethod
    def _find_latest_interval_series(borehole: etree._Element) -> etree._Element | None:
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


    def _parse_single_layer(self,
        interval: etree._Element,
        *,
        borehole_id: str,
        index: int,
        ansatzhoehe_nn: float,
    ) -> BoreholeLayer | None:
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

        hauptgemengteil, nebengemengteil, rock_color = self._parse_lithology_components(interval)
        genese = _text(interval, f"{{{BML_NS}}}genesis")
        geogenese = _text(interval, f"{{{BML_NS}}}geoGenesis")
        visual_rgb, din_color_name = self._mappings.visual_color_for_hauptgemengteil(hauptgemengteil)

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
        layer.psets = self._build_layer_psets(layer)
        return layer


    def _parse_lithology_components(self, interval: etree._Element) -> tuple[str, str, str]:
        """Resolve the soil components and colour of one ``bml:Interval``.

        ``bml:rockCode`` is preferred because the dominant component often has no
        ``RockNameList`` entry and therefore an empty ``rockName`` (e.g. ``F`` for
        Mudde at 64 %), which would otherwise promote a minor component. The
        ``bml:lithology`` blocks are the fallback, sorted by ``percentage``.

        Returns:
            ``(hauptgemengteil, nebengemengteil, farbe)``.
        """
        color = ""
        entries: list[tuple[float, str]] = []
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
        rock_codes = [name for _, name in entries]
        if not rock_codes:
            return ("", "", color)
        return (rock_codes[0], ", ".join(rock_codes[1:]), color)


    def _parse_groundwater(self, borehole: etree._Element, borehole_id: str) -> BoreholeWater | None:
        """
        Read the groundwater information (``bml:entryDepth``, ``bml:balancedLevel``, ``bml:endLevel``) and build one :class:`BoreholeWater`; ``None`` when unusable.
        """
        entry_depth = _float_or_none(_text(borehole, f"{{{BML_NS}}}groundwater/{{{BML_NS}}}Groundwater/{{{BML_NS}}}entryDepth"))
        if entry_depth is None:
            logger.warning("Borehole %s: missing groundwater entry depth; skipped", borehole_id)
            return None
    
        balanced_level = _float_or_none(_text(borehole, f"{{{BML_NS}}}groundwater/{{{BML_NS}}}Groundwater/{{{BML_NS}}}balancedLevel"))
        end_level = _float_or_none(_text(borehole, f"{{{BML_NS}}}groundwater/{{{BML_NS}}}Groundwater/{{{BML_NS}}}endLevel"))

        water = BoreholeWater(entry_depth=entry_depth)
        water.psets = self._build_water_psets(water)
        return water


    def _build_layer_psets(self, layer: BoreholeLayer) -> dict[str, BaseModel]:
        """Build the layer-level pset templates with codes resolved."""
        aufschlussbereich = Pset_Aufschlussbereich_Borehole(
            bodenart=self._mappings.map_hauptgemengteil(layer.hauptgemengteil),
            bodenart_ergaenzung=self._mappings.map_nebengemengteil(layer.nebengemengteil),
            farbe=self._mappings.map_rock_color(layer.farbe),
            kalkgehalt=self._mappings.map_carbonate(layer.kalkgehalt),
            stratigrafie=self._mappings.map_chronostratigraphy(layer.stratigraphie),
        )
        schicht = Pset_Schicht_Borehole(
            genese=self._mappings.map_genesis(layer.genese),
            geogenese=self._mappings.map_geogenesis(layer.geogenese),
            bodenkonsistenz=self._mappings.map_consistency(layer.konsistenz),
            geologische_bezeichnung=layer.rock_name_text or UNDEFINED,
        )
        objektinformation = Pset_Objektinformation_Borehole()

        return {
            Pset_Aufschlussbereich_Borehole.pset_name: aufschlussbereich,
            Pset_Schicht_Borehole.pset_name: schicht,
            Pset_Objektinformation_Water.pset_name: objektinformation,
        }


    def _build_water_psets(self, water: BoreholeWater) -> dict[str, BaseModel]:
        """Build the groundwater pset templates."""
        wasser = Pset_Wasser_Water(wasserstandhoehe=water.entry_depth)
        schicht = Pset_Schicht_Water(schichtnummer=UNDEFINED)
        objektinformation = Pset_Objektinformation_Water()

        return {
            Pset_Wasser_Water.pset_name: wasser,
            Pset_Schicht_Water.pset_name: schicht,
            Pset_Objektinformation_Water.pset_name: objektinformation,
        }    


__all__ = [
    "BoreholeMLProcessor"
]