"""Tests for the BoreholeML parser, the DIN mappings and the boreholes app.

These cover the pure pieces that don't need a full IFC environment: soil and
colour code mapping, ``rockCode`` splitting, XML → records (including the
depth-to-NHN conversion), and the pset templates. A smoke test asserts that
``BoreholesGenericApp.build_ifc`` handles the empty-records case without
crashing.
"""

from __future__ import annotations

import pytest
from lxml import etree
from pydantic import BaseModel

from BIMFabrikHH_core.apps.boreholes import BoreholesGenericApp
from BIMFabrikHH_core.apps.boreholes.helper import UNDEFINED, _split_rock_code
from BIMFabrikHH_core.apps.boreholes.mappings import BoreholeMappings
from BIMFabrikHH_core.apps.boreholes.processing import (BOREHOLE_PORTAL_SID,
                                                        BOREHOLE_PORTAL_URL,
                                                        BoreholeMLProcessor)
from BIMFabrikHH_core.data_models.boreholes import (BoreholeRecord,
                                                    BoreholeWater,
                                                    collect_borehole_psets,
                                                    collect_groundwater_psets)
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_boreholes import (
    Pset_Aufschluss_Borehole, Pset_Aufschlussbereich_Borehole,
    Pset_Objektinformation_Borehole, Pset_Schicht_Borehole)
from BIMFabrikHH_core.data_models.pydantic_psets_groundwater import (
    Pset_Objektinformation_Groundwater, Pset_Schicht_Groundwater,
    Pset_Wasser_Groundwater)

BML = "http://www.infogeo.de/boreholeml/3.0"
GML = "http://www.opengis.net/gml/3.2"
GMD = "http://www.isotc211.org/2005/gmd"


@pytest.fixture
def mappings() -> BoreholeMappings:
    return BoreholeMappings.load_default()


@pytest.fixture
def processor(mappings: BoreholeMappings) -> BoreholeMLProcessor:
    return BoreholeMLProcessor(mappings=mappings)


def _borehole_xml(
    *,
    borehole_id: str = "BDHH_TEST1",
    pos: str = "565084.160 5934034.654 14.300",
    intervals: str = "",
    groundwater: str = "",
) -> bytes:
    """Minimal ``wfs:FeatureCollection`` with a single ``bml:Borehole``."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
                       xmlns:bml="{BML}" xmlns:gml="{GML}" xmlns:gmd="{GMD}">
  <wfs:member>
    <bml:Borehole gml:id="{borehole_id}">
      <bml:location>
        <gml:Point gml:id="{borehole_id}_LOC" srsName="urn:ogc:def:crs:EPSG::5555">
          <gml:pos>{pos}</gml:pos>
        </gml:Point>
      </bml:location>
      <bml:id>{borehole_id}</bml:id>
      <bml:shortName><gmd:LocalisedCharacterString>B1</gmd:LocalisedCharacterString></bml:shortName>
      <bml:fullName><gmd:LocalisedCharacterString>B.45</gmd:LocalisedCharacterString></bml:fullName>
      <bml:totalLength uom="m">5.5</bml:totalLength>
      {groundwater}
      <bml:drillingMethod>UN</bml:drillingMethod>
      <bml:drillingDate>1936-06-26</bml:drillingDate>
      <bml:project>Hbg.-Wexstr.</bml:project>
      <bml:intervalSeries>
        <bml:IntervalSeries>
          <bml:version>0</bml:version>
          {intervals}
        </bml:IntervalSeries>
      </bml:intervalSeries>
    </bml:Borehole>
  </wfs:member>
</wfs:FeatureCollection>""".encode()


def _interval(
    *,
    from_depth: str,
    to_depth: str,
    rock_code: str = "",
    rock_name_text: str = "",
    strat: str = "",
    geo_genesis: str = "",
    lithologies: str = "",
) -> str:
    rock_code_el = f"<bml:rockCode>{rock_code}</bml:rockCode>" if rock_code else ""
    return f"""
    <bml:layer>
      <bml:Interval>
        <bml:from uom="m">{from_depth}</bml:from>
        <bml:to uom="m">{to_depth}</bml:to>
        {rock_code_el}
        <bml:rockNameText>
          <gmd:LocalisedCharacterString>{rock_name_text}</gmd:LocalisedCharacterString>
        </bml:rockNameText>
        <bml:geoGenesis>{geo_genesis}</bml:geoGenesis>
        <bml:carbonateContent>c3</bml:carbonateContent>
        <bml:consistency/>
        {lithologies}
        <bml:stratigraphy>
          <bml:Stratigraphy>
            <bml:chronoStratigraphy>{strat}</bml:chronoStratigraphy>
          </bml:Stratigraphy>
        </bml:stratigraphy>
      </bml:Interval>
    </bml:layer>"""


def _groundwater(*, entry_depth: str = "", balanced_level: str = "", end_level: str = "") -> str:
    return f"""
      <bml:groundwater>
        <bml:Groundwater>
          <bml:entryDepth uom="m">{entry_depth}</bml:entryDepth>
          <bml:balancedLevel uom="m">{balanced_level}</bml:balancedLevel>
          <bml:endLevel uom="m">{end_level}</bml:endLevel>
        </bml:Groundwater>
      </bml:groundwater>
    """


def _lithology(rock_name: str = "", percentage: str = "", rock_color: str = "") -> str:
    return f"""
        <bml:lithology>
          <bml:Lithology>
            <bml:rockName>{rock_name}</bml:rockName>
            <bml:percentage>{percentage}</bml:percentage>
            <bml:rockColor>{rock_color}</bml:rockColor>
          </bml:Lithology>
        </bml:lithology>"""


# ---------------------------------------------------------------------------
# BoreholeMappings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("mS", "mS (Mittelsand)"),
        ("ffS", "ffS (Feinstsand)"),
        ("S", "S (Sand)"),
        ("U", "U (Schluff)"),
        ("T", "T (Ton)"),
        ("H", "H (Torf / Humus)"),
    ],
)
def test_map_soil_symbol_resolves_din_codes(
    mappings: BoreholeMappings,
    code: str,
    expected: str,
) -> None:
    assert mappings.map_soil_symbol(code) == expected


def test_map_soil_symbol_returns_undefined_for_blank(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_soil_symbol("") == UNDEFINED
    assert mappings.map_soil_symbol(None) == UNDEFINED


def test_map_soil_symbol_passes_through_unknown_code(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_soil_symbol("zzz") == "zzz"


def test_map_soil_symbol_maps_combinatoric_notation(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_soil_symbol("uS") == "uS (schluffiger Sand)"


def test_map_soil_symbol_hauptgemengteil_splits_comma_list(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_hauptgemengteil("mS, fS") == "mS (Mittelsand), fS (Feinsand)"


def test_map_soil_symbol_nebengemengteil_maps_each_component(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_nebengemengteil("g, s") == "g (kiesig), s (sandig)"


def test_map_soil_symbol_multiple_main_components(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_hauptgemengteil("mS(fs), S") == "mS (Mittelsand), S (Sand)"

    assert mappings.map_nebengemengteil("mS(fs), S") == "fs (feinsandig)"


def test_map_soil_symbol_with_hyphen(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_hauptgemengteil("gG-fG") == "gG-fG (Grobkies-Feinkies)"


def test_map_soil_symbol_brackets_around_main_component(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_hauptgemengteil("(gG-fG)(x)") == "gG-fG (Grobkies-Feinkies)"

    assert mappings.map_nebengemengteil("(gG-fG)(x)") == "x (steinig)"


def test_map_soil_symbol_multiple_side_components(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_hauptgemengteil("fG(gs, ms, x)") == "fG (Feinkies)"

    assert mappings.map_nebengemengteil("fG(gs, ms, x)") == "gs (grobsandig), ms (mittelsandig), x (steinig)"


def test_map_nebengemengteil_returns_undefined_for_blank(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_nebengemengteil("") == UNDEFINED


def test_map_din_color_appends_german_name(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_din_color("gr") == "gr (grau)"


def test_map_din_color_passes_through_unknown_code(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_din_color("h8") == "h8"


def test_map_stratigraphy_appends_german_name(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_chronostratigraphy("qh") == "qh (Quartär holozän)"


def test_map_stratigraphy_returns_undefined_for_blank(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.map_chronostratigraphy("") == UNDEFINED


def test_visual_color_uses_soil_code_not_farbe(
    mappings: BoreholeMappings,
) -> None:
    rgb, name = mappings.visual_color_for_hauptgemengteil("mS")

    assert name == "orange"
    assert rgb == (198, 84, 47)


def test_visual_color_falls_back_to_table_default(
    mappings: BoreholeMappings,
) -> None:
    rgb, name = mappings.visual_color_for_hauptgemengteil("unknown-code")

    assert name == "weiß"
    assert rgb == (254, 254, 254)


def test_visual_color_is_case_insensitive(
    mappings: BoreholeMappings,
) -> None:
    assert mappings.visual_color_for_hauptgemengteil("ffs") == mappings.visual_color_for_hauptgemengteil("ffS")


# ---------------------------------------------------------------------------
# _split_rock_code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rock_code", "expected"),
    [
        ("F(s4, hz4, ht2)", ("F", "s4, hz4, ht2")),
        ("ffS(x)", ("ffS", "x")),
        ("mS(fs), S", ("mS, S", "fs")),
        ("mS, yy", ("mS", "yy")),
        ("H", ("H", "")),
        ("", ("", "")),
    ],
)
def test_split_rock_code_handles_both_notations(rock_code: str, expected: tuple) -> None:
    assert _split_rock_code(rock_code) == expected


# ---------------------------------------------------------------------------
# BoreholeMLProcessor.parse
# ---------------------------------------------------------------------------


def test_processor_parse_accepts_xml_string(processor):
    xml = _borehole_xml(intervals=_interval(from_depth="0", to_depth="1", rock_code="mS")).decode()

    assert len(processor.parse(xml)) == 1


def test_processor_parse_accepts_element(processor):
    root = etree.fromstring(_borehole_xml(intervals=_interval(from_depth="0", to_depth="1", rock_code="mS")))

    assert len(processor.parse(root)) == 1


def test_processor_parse_accepts_element_tree(processor):
    root = etree.fromstring(_borehole_xml(intervals=_interval(from_depth="0", to_depth="1", rock_code="mS")))

    assert len(processor.parse(etree.ElementTree(root))) == 1


def test_processor_parse_accepts_path(processor, tmp_path):
    path = tmp_path / "boreholes.xml"
    path.write_bytes(_borehole_xml(intervals=_interval(from_depth="0", to_depth="1", rock_code="mS")))

    assert len(processor.parse(path)) == 1
    assert len(processor.from_file(path)) == 1


def test_processor_parse_reads_head_data(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS, yy"))

    records = processor.parse(xml)

    assert len(records) == 1
    record = records[0]
    assert record.borehole_id == "BDHH_TEST1"
    assert record.aufschlussbezeichnung == "B.45"
    assert record.easting == pytest.approx(565084.160)
    assert record.northing == pytest.approx(5934034.654)
    assert record.ansatzhoehe_nn == pytest.approx(14.3)
    assert record.endteufe == pytest.approx(5.5)
    assert record.bohrdatum == "1936-06-26"
    assert record.bohrvorgang == "UN (unbekanntes Bohrverfahren)"
    assert record.projekt == "Hbg.-Wexstr."


def test_processor_parse_converts_depth_to_nhn(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS")
        + _interval(from_depth="2.5", to_depth="5.5", rock_code="T")
    )
    layers = processor.parse(xml)[0].layers

    assert [layer.from_depth for layer in layers] == [0.0, 2.5]
    # Ansatzpunkt 14.3 m NHN, depths measured downwards from there.
    assert layers[0].upper_height == pytest.approx(14.3)
    assert layers[0].lower_height == pytest.approx(11.8)
    assert layers[0].thickness == pytest.approx(2.5)
    assert layers[1].lower_height == pytest.approx(8.8)
    assert layers[1].thickness == pytest.approx(3.0)


def test_processor_parse_orders_layers_top_down(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="2.5", to_depth="5.5", rock_code="T")
        + _interval(from_depth="0.0", to_depth="2.5", rock_code="mS")
    )
    layers = processor.parse(xml)[0].layers
    assert [layer.upper_height for layer in layers] == sorted((layer.upper_height for layer in layers), reverse=True)


def test_processor_parse_reads_groundwater(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="20.0", rock_code="mS"),
        groundwater=_groundwater(entry_depth="7.3", balanced_level="6.5", end_level="14.7"),
    )

    records = processor.parse(xml)

    assert len(records) == 1
    groundwater = records[0].groundwater

    assert groundwater is not None
    assert groundwater.entry_depth == pytest.approx(7.3)
    assert groundwater.balanced_level == pytest.approx(6.5)
    assert groundwater.end_level == pytest.approx(14.7)


def test_processor_parse_skips_groundwater_without_entry_depth(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="20.0", rock_code="mS"),
        groundwater=_groundwater(entry_depth=None, balanced_level="6.5", end_level="14.7"),
    )

    records = processor.parse(xml)

    assert len(records) == 1
    assert records[0].groundwater is None


@pytest.mark.parametrize(
    ("balanced_level", "end_level", "expected_balanced", "expected_end"),
    [
        ("", "11.8", None, 11.8),
        ("12.1", "", 12.1, None),
        ("invalid", "11.8", None, 11.8),
        ("12.1", "invalid", 12.1, None),
    ],
)
def test_processor_parse_allows_missing_or_invalid_optional_groundwater_levels(
    processor: BoreholeMLProcessor, balanced_level, end_level, expected_balanced, expected_end
) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="20.0", rock_code="mS"),
        groundwater=_groundwater(entry_depth="7.3", balanced_level=balanced_level, end_level=end_level),
    )

    records = processor.parse(xml)
    groundwater = records[0].groundwater

    assert len(records) == 1
    assert groundwater is not None
    assert groundwater.entry_depth == pytest.approx(7.3)

    assert groundwater.balanced_level == pytest.approx(expected_balanced)
    assert groundwater.end_level == pytest.approx(expected_end)


def test_processor_parse_prefers_rock_code_over_lithology(processor: BoreholeMLProcessor) -> None:
    """The dominant component often has an empty ``rockName`` (F = Mudde at 64 %)."""
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="4.3",
            to_depth="5.4",
            rock_code="F(s4, hz4, ht2)",
            rock_name_text="Mudde (stark sandig)",
            lithologies=_lithology(rock_name="", percentage="63.64") + _lithology(rock_name="S", percentage="36.36"),
        )
    )
    layer = processor.parse(xml)[0].layers[0]
    assert layer.hauptgemengteil == "F"
    assert layer.nebengemengteil == "s4, hz4, ht2"
    assert layer.rock_name_text == "Mudde (stark sandig)"


def test_processor_parse_falls_back_to_lithology_by_percentage(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="1.0",
            lithologies=_lithology(rock_name="S", percentage="30.0") + _lithology(rock_name="mS", percentage="70.0"),
        )
    )
    layer = processor.parse(xml)[0].layers[0]
    assert layer.hauptgemengteil == "mS"
    assert layer.nebengemengteil == "S"


def test_processor_parse_takes_first_non_empty_rock_color(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="1.0",
            rock_code="fS(x)",
            lithologies=_lithology(rock_name="fS", percentage="72.73", rock_color="h8"),
        )
    )
    assert processor.parse(xml)[0].layers[0].farbe == "h8"


def test_processor_parse_skips_zero_thickness_layers(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="1.0", to_depth="1.0", rock_code="mS")
        + _interval(from_depth="0.0", to_depth="1.0", rock_code="T")
    )
    layers = processor.parse(xml)[0].layers
    assert len(layers) == 1
    assert layers[0].hauptgemengteil == "T"


def test_processor_parse_skips_borehole_without_layers(processor: BoreholeMLProcessor) -> None:
    assert processor.parse(_borehole_xml(intervals="")) == []


def test_processor_parse_skips_borehole_without_position(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        pos="565084.160",
        intervals=_interval(from_depth="0.0", to_depth="1.0", rock_code="mS"),
    )
    assert processor.parse(xml) == []


def test_processor_parse_uses_two_dimensional_position(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        pos="565084.160 5934034.654",
        intervals=_interval(from_depth="0.0", to_depth="1.0", rock_code="mS"),
    )
    record = processor.parse(xml)[0]
    assert record.ansatzhoehe_nn == pytest.approx(0.0)
    assert record.layers[0].lower_height == pytest.approx(-1.0)


def test_processor_parse_rejects_unsupported_source(processor: BoreholeMLProcessor) -> None:
    with pytest.raises(TypeError):
        processor.parse(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BoreholeWater
# ---------------------------------------------------------------------------


def test_borehole_water_allows_optional_levels():
    water = BoreholeWater(
        entry_depth=3.2,
        balanced_level=None,
        end_level=11.5,
    )

    assert water.entry_depth == 3.2
    assert water.balanced_level is None
    assert water.end_level == 11.5
    assert water.psets == {}


# ---------------------------------------------------------------------------
# psets
# ---------------------------------------------------------------------------


def test_parsed_record_carries_expected_psets(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="20.5",
            rock_code="mS, yy",
            rock_name_text="Mittelsand, Bauschutt",
            strat="qh",
            geo_genesis="yf",
        ),
        groundwater=_groundwater(entry_depth="7.3", balanced_level="6.5", end_level="14.7"),
    )
    record = processor.parse(xml)[0]
    layer = record.layers[0]
    groundwater = record.groundwater

    assert set(record.psets) == {"Pset_Aufschluss", "Pset_Hyperlink"}
    assert set(layer.psets) == {"Pset_Aufschlussbereich", "Pset_Schicht", "Pset_Objektinformation"}
    assert set(groundwater.psets) == {"Pset_Wasser", "Pset_Schicht", "Pset_Objektinformation"}

    record_aufschluss = record.psets["Pset_Aufschluss"]
    assert isinstance(record_aufschluss, Pset_Aufschluss_Borehole)
    assert record_aufschluss.aufschlussart == "Bohrung"
    assert record_aufschluss.aufschlussnummer == "B.45"
    assert record_aufschluss.hoehenansatzpunkt == pytest.approx(14.3)

    layer_bereich = layer.psets["Pset_Aufschlussbereich"]
    assert isinstance(layer_bereich, Pset_Aufschlussbereich_Borehole)
    assert layer_bereich.bodenart == "mS (Mittelsand)"
    assert layer_bereich.bohrvorgang == "UN (unbekanntes Bohrverfahren)"
    assert layer_bereich.kalkgehalt == "c3 (karbonathaltig)"
    assert layer_bereich.stratigrafie.startswith("qh (")

    layer_schicht = layer.psets["Pset_Schicht"]
    assert isinstance(layer_schicht, Pset_Schicht_Borehole)
    assert layer_schicht.genese == UNDEFINED
    assert layer_schicht.geogenese == "yf (Auffüllung)"
    assert layer_schicht.geologische_bezeichnung == "Mittelsand, Bauschutt"
    assert layer_schicht.bodenkonsistenz == UNDEFINED

    assert isinstance(layer.psets["Pset_Objektinformation"], Pset_Objektinformation_Borehole)

    water_wasser = groundwater.psets["Pset_Wasser"]
    assert isinstance(water_wasser, Pset_Wasser_Groundwater)
    assert water_wasser.wasserstandhoehe == pytest.approx(7.3)

    water_schicht = groundwater.psets["Pset_Schicht"]
    assert isinstance(water_schicht, Pset_Schicht_Groundwater)
    assert water_schicht.schichtnummer == UNDEFINED

    assert isinstance(groundwater.psets["Pset_Objektinformation"], Pset_Objektinformation_Groundwater)


def test_collect_borehole_psets_merges_both_levels(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = processor.parse(xml)[0]
    psets = collect_borehole_psets(record, record.layers[0])

    assert len(psets) == 5
    assert all(isinstance(pset, BaseModel) for pset in psets)
    assert isinstance(psets[0], Pset_Aufschluss_Borehole)
    assert {type(pset) for pset in psets} == {
        Pset_Aufschluss_Borehole,
        Pset_Hyperlink,
        Pset_Aufschlussbereich_Borehole,
        Pset_Schicht_Borehole,
        Pset_Objektinformation_Borehole,
    }


def test_collect_groundwater_psets_merges_both_levels(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="20.5", rock_code="mS"),
        groundwater=_groundwater(entry_depth="7.3", balanced_level="6.5", end_level="14.7"),
    )
    record = processor.parse(xml)[0]
    psets = collect_groundwater_psets(record)

    assert len(psets) == 5
    assert all(isinstance(pset, BaseModel) for pset in psets)
    assert {type(pset) for pset in psets} == {
        Pset_Aufschluss_Borehole,
        Pset_Hyperlink,
        Pset_Wasser_Groundwater,
        Pset_Schicht_Groundwater,
        Pset_Objektinformation_Groundwater,
    }


def test_collect_borehole_psets_can_be_disabled(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = processor.parse(xml)[0]
    assert collect_borehole_psets(record, record.layers[0], include_property_sets=False) == []


def test_collect_water_psets_can_be_disabled(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="20.5", rock_code="mS"),
        groundwater=_groundwater(entry_depth="7.3", balanced_level="6.5", end_level="14.7"),
    )
    record = processor.parse(xml)[0]
    assert collect_groundwater_psets(record, include_property_sets=False) == []


def test_collect_borehole_psets_skips_non_pydantic_values(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = processor.parse(xml)[0]
    record.psets = {"broken": "not-a-model"}  # type: ignore[dict-item]
    psets = collect_borehole_psets(record, record.layers[0])
    assert len(psets) == 3


def test_serialized_pset_uses_bimhh_aliases() -> None:
    dumped = Pset_Aufschlussbereich_Borehole(bodenart="mS (Mittelsand)").model_dump(by_alias=True)
    assert dumped["_Bodenart"] == "mS (Mittelsand)"


# ---------------------------------------------------------------------------
# BoreholeMLProcessor._build_borehole_hyperlink
# ---------------------------------------------------------------------------


def test_build_borehole_hyperlink_accepts_numeric_portal_id() -> None:
    """The portal expects the numeric Archivnummer, which can be passed as a string or integer."""
    pset = BoreholeMLProcessor._build_borehole_hyperlink(50300, "B.IX/182")
    assert pset.hyperlink_001 == f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id=50300"
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung B.IX/182 (ID: 50300)"


def test_build_borehole_hyperlink_accepts_string_portal_id() -> None:
    """The portal expects the numeric Archivnummer, which can be passed as a string or integer."""
    pset = BoreholeMLProcessor._build_borehole_hyperlink("50300", "B.IX/182")
    assert pset.hyperlink_001 == f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id=50300"
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung B.IX/182 (ID: 50300)"


def test_build_borehole_hyperlink_without_designation() -> None:
    pset = BoreholeMLProcessor._build_borehole_hyperlink("50300")
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung (ID: 50300)"


def test_parsed_record_carries_portal_hyperlink(processor: BoreholeMLProcessor) -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = processor.parse(xml)[0]
    hyperlink = record.psets["Pset_Hyperlink"]
    assert isinstance(hyperlink, Pset_Hyperlink)
    assert hyperlink.hyperlink_001.endswith("&id=")
    assert BOREHOLE_PORTAL_SID in hyperlink.hyperlink_001


# ---------------------------------------------------------------------------
# BoreholesGenericApp
# ---------------------------------------------------------------------------


def test_build_ifc_returns_none_for_empty_records() -> None:
    request_params = RequestParams(bbox=BoundingBoxParams(min_x=9.98, min_y=53.54, max_x=10.00, max_y=53.56))
    result = BoreholesGenericApp.build_ifc([], request_params=request_params)
    assert result is None


def test_build_ifc_returns_none_when_records_have_no_layers() -> None:
    request_params = RequestParams(bbox=BoundingBoxParams(min_x=9.98, min_y=53.54, max_x=10.00, max_y=53.56))
    record = BoreholeRecord(
        borehole_id="BDHH_TEST1",
        archive_id="",
        easting=565084.16,
        northing=5934034.654,
        ansatzhoehe_nn=14.3,
        groundwater=None,
    )
    assert BoreholesGenericApp.build_ifc([record], request_params=request_params) is None
