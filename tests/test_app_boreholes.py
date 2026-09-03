"""Tests for the BoreholeML parser, the DIN mappings and the boreholes app.

These cover the pure pieces that don't need a full IFC environment: soil and
colour code mapping, ``rockCode`` splitting, XML → records (including the
depth-to-NHN conversion), and the pset templates. A smoke test asserts that
``BoreholesGenericApp.build_ifc`` handles the empty-records case without
crashing.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from BIMFabrikHH_core.apps.boreholes import (
    BOREHOLE_PORTAL_SID,
    BOREHOLE_PORTAL_URL,
    BoreholeRecord,
    BoreholesGenericApp,
    build_borehole_hyperlink,
    collect_borehole_psets,
    map_color_code,
    map_hauptgemengteil,
    map_nebengemengteil,
    map_soil_symbol,
    map_stratigraphy,
    records_from_boreholeml,
    visual_color_for_hauptgemengteil,
)
from BIMFabrikHH_core.apps.boreholes.processing import UNDEFINED, _split_rock_code
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_boreholes import (
    Pset_Aufschluss,
    Pset_Aufschlussbereich,
    Pset_Objektinformation_Borehole,
    Pset_Schicht,
)

BML = "http://www.infogeo.de/boreholeml/3.0"
GML = "http://www.opengis.net/gml/3.2"
GMD = "http://www.isotc211.org/2005/gmd"


def _borehole_xml(
    *,
    borehole_id: str = "BDHH_TEST1",
    pos: str = "565084.160 5934034.654 14.300",
    intervals: str = "",
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
# map_soil_symbol / map_hauptgemengteil / map_nebengemengteil
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
def test_map_soil_symbol_resolves_din_codes(code: str, expected: str) -> None:
    assert map_soil_symbol(code) == expected


def test_map_soil_symbol_returns_undefined_for_blank() -> None:
    assert map_soil_symbol("") == UNDEFINED
    assert map_soil_symbol(None) == UNDEFINED


def test_map_soil_symbol_passes_through_unknown_code() -> None:
    assert map_soil_symbol("zzz") == "zzz"


def test_map_soil_symbol_maps_combinatoric_notation() -> None:
    assert map_soil_symbol("uS") == "uS (schluffiger Sand)"


def test_map_hauptgemengteil_splits_comma_list() -> None:
    assert map_hauptgemengteil("mS, fS") == "mS (Mittelsand), fS (Feinsand)"


def test_map_nebengemengteil_maps_each_component() -> None:
    assert map_nebengemengteil("g, s") == "g (kiesig), s (sandig)"


def test_map_nebengemengteil_returns_undefined_for_blank() -> None:
    assert map_nebengemengteil("") == UNDEFINED


# ---------------------------------------------------------------------------
# map_color_code / map_stratigraphy / visual_color_for_hauptgemengteil
# ---------------------------------------------------------------------------


def test_map_color_code_appends_german_name() -> None:
    assert map_color_code("gr") == "gr (grau)"


def test_map_color_code_passes_through_unknown_code() -> None:
    # BoreholeML uses its own RockColorList, so codes like h8 are not in the DIN table.
    assert map_color_code("h8") == "h8"


def test_map_stratigraphy_appends_german_name() -> None:
    assert map_stratigraphy("qh") == "qh (Quartär holozän)"


def test_map_stratigraphy_returns_undefined_for_blank() -> None:
    assert map_stratigraphy("") == UNDEFINED


def test_visual_color_uses_soil_code_not_farbe() -> None:
    rgb, name = visual_color_for_hauptgemengteil("mS")
    assert name == "orange"
    assert rgb == (198, 84, 47)


def test_visual_color_falls_back_to_table_default() -> None:
    rgb, name = visual_color_for_hauptgemengteil("unknown-code")
    assert name == "weiß"
    assert rgb == (254, 254, 254)


def test_visual_color_is_case_insensitive() -> None:
    assert visual_color_for_hauptgemengteil("ffs") == visual_color_for_hauptgemengteil("ffS")


# ---------------------------------------------------------------------------
# _split_rock_code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rock_code", "expected"),
    [
        ("F(s4, hz4, ht2)", ("F", "s4, hz4, ht2")),
        ("ffS(x)", ("ffS", "x")),
        ("mS, yy", ("mS", "yy")),
        ("H", ("H", "")),
        ("", ("", "")),
    ],
)
def test_split_rock_code_handles_both_notations(rock_code: str, expected: tuple) -> None:
    assert _split_rock_code(rock_code) == expected


# ---------------------------------------------------------------------------
# records_from_boreholeml
# ---------------------------------------------------------------------------


def test_records_from_boreholeml_reads_head_data() -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS, yy"))
    records = records_from_boreholeml(xml)

    assert len(records) == 1
    record = records[0]
    assert record.borehole_id == "BDHH_TEST1"
    assert record.aufschlussbezeichnung == "B.45"
    assert record.easting == pytest.approx(565084.160)
    assert record.northing == pytest.approx(5934034.654)
    assert record.ansatzhoehe_nn == pytest.approx(14.3)
    assert record.endteufe == pytest.approx(5.5)
    assert record.bohrdatum == "1936-06-26"
    assert record.bohrvorgang == "UN"
    assert record.projekt == "Hbg.-Wexstr."


def test_records_from_boreholeml_converts_depth_to_nhn() -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS")
        + _interval(from_depth="2.5", to_depth="5.5", rock_code="T")
    )
    layers = records_from_boreholeml(xml)[0].layers

    assert [layer.from_depth for layer in layers] == [0.0, 2.5]
    # Ansatzpunkt 14.3 m NHN, depths measured downwards from there.
    assert layers[0].upper_height == pytest.approx(14.3)
    assert layers[0].lower_height == pytest.approx(11.8)
    assert layers[0].thickness == pytest.approx(2.5)
    assert layers[1].lower_height == pytest.approx(8.8)
    assert layers[1].thickness == pytest.approx(3.0)


def test_records_from_boreholeml_orders_layers_top_down() -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="2.5", to_depth="5.5", rock_code="T")
        + _interval(from_depth="0.0", to_depth="2.5", rock_code="mS")
    )
    layers = records_from_boreholeml(xml)[0].layers
    assert [layer.upper_height for layer in layers] == sorted((layer.upper_height for layer in layers), reverse=True)


def test_records_from_boreholeml_prefers_rock_code_over_lithology() -> None:
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
    layer = records_from_boreholeml(xml)[0].layers[0]
    assert layer.hauptgemengteil == "F"
    assert layer.nebengemengteil == "s4, hz4, ht2"
    assert layer.rock_name_text == "Mudde (stark sandig)"


def test_records_from_boreholeml_falls_back_to_lithology_by_percentage() -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="1.0",
            lithologies=_lithology(rock_name="S", percentage="30.0") + _lithology(rock_name="mS", percentage="70.0"),
        )
    )
    layer = records_from_boreholeml(xml)[0].layers[0]
    assert layer.hauptgemengteil == "mS"
    assert layer.nebengemengteil == "S"


def test_records_from_boreholeml_takes_first_non_empty_rock_color() -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="1.0",
            rock_code="fS(x)",
            lithologies=_lithology(rock_name="fS", percentage="72.73", rock_color="h8"),
        )
    )
    assert records_from_boreholeml(xml)[0].layers[0].farbe == "h8"


def test_records_from_boreholeml_skips_zero_thickness_layers() -> None:
    xml = _borehole_xml(
        intervals=_interval(from_depth="1.0", to_depth="1.0", rock_code="mS")
        + _interval(from_depth="0.0", to_depth="1.0", rock_code="T")
    )
    layers = records_from_boreholeml(xml)[0].layers
    assert len(layers) == 1
    assert layers[0].hauptgemengteil == "T"


def test_records_from_boreholeml_skips_borehole_without_layers() -> None:
    assert records_from_boreholeml(_borehole_xml(intervals="")) == []


def test_records_from_boreholeml_skips_borehole_without_position() -> None:
    xml = _borehole_xml(
        pos="565084.160",
        intervals=_interval(from_depth="0.0", to_depth="1.0", rock_code="mS"),
    )
    assert records_from_boreholeml(xml) == []


def test_records_from_boreholeml_uses_two_dimensional_position() -> None:
    xml = _borehole_xml(
        pos="565084.160 5934034.654",
        intervals=_interval(from_depth="0.0", to_depth="1.0", rock_code="mS"),
    )
    record = records_from_boreholeml(xml)[0]
    assert record.ansatzhoehe_nn == pytest.approx(0.0)
    assert record.layers[0].lower_height == pytest.approx(-1.0)


def test_records_from_boreholeml_rejects_unsupported_source() -> None:
    with pytest.raises(TypeError):
        records_from_boreholeml(42)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# psets
# ---------------------------------------------------------------------------


def test_parsed_record_carries_expected_psets() -> None:
    xml = _borehole_xml(
        intervals=_interval(
            from_depth="0.0",
            to_depth="2.5",
            rock_code="mS, yy",
            rock_name_text="Mittelsand, Bauschutt",
            strat="qh",
            geo_genesis="yf",
        )
    )
    record = records_from_boreholeml(xml)[0]
    layer = record.layers[0]

    assert set(record.psets) == {"Pset_Aufschluss", "Pset_Hyperlink"}
    assert set(layer.psets) == {"Pset_Aufschlussbereich", "Pset_Schicht", "Pset_Objektinformation"}

    aufschluss = record.psets["Pset_Aufschluss"]
    assert isinstance(aufschluss, Pset_Aufschluss)
    assert aufschluss.aufschlussart == "Bohrung"
    assert aufschluss.aufschlussnummer == "B.45"
    assert aufschluss.hoehenansatzpunkt == pytest.approx(14.3)

    bereich = layer.psets["Pset_Aufschlussbereich"]
    assert isinstance(bereich, Pset_Aufschlussbereich)
    assert bereich.bodenart == "mS (Mittelsand)"
    assert bereich.bohrvorgang == "UN"
    assert bereich.kalkgehalt == "c3"
    assert bereich.stratigrapfie.startswith("qh (")

    schicht = layer.psets["Pset_Schicht"]
    assert isinstance(schicht, Pset_Schicht)
    assert schicht.genese == "yf"
    assert schicht.geologische_bezeichnung == "Mittelsand, Bauschutt"
    assert schicht.bodenkonsistenz == UNDEFINED

    assert isinstance(layer.psets["Pset_Objektinformation"], Pset_Objektinformation_Borehole)


def test_collect_borehole_psets_merges_both_levels() -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = records_from_boreholeml(xml)[0]
    psets = collect_borehole_psets(record, record.layers[0])

    assert len(psets) == 5
    assert all(isinstance(pset, BaseModel) for pset in psets)
    assert isinstance(psets[0], Pset_Aufschluss)
    assert {type(pset) for pset in psets} == {
        Pset_Aufschluss,
        Pset_Hyperlink,
        Pset_Aufschlussbereich,
        Pset_Schicht,
        Pset_Objektinformation_Borehole,
    }


def test_collect_borehole_psets_can_be_disabled() -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = records_from_boreholeml(xml)[0]
    assert collect_borehole_psets(record, record.layers[0], include_property_sets=False) == []


def test_collect_borehole_psets_skips_non_pydantic_values() -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = records_from_boreholeml(xml)[0]
    record.psets = {"broken": "not-a-model"}  # type: ignore[dict-item]
    psets = collect_borehole_psets(record, record.layers[0])
    assert len(psets) == 3


def test_build_borehole_hyperlink_uses_fixed_portal_part_plus_id() -> None:
    pset = build_borehole_hyperlink("BDHH_6434B1", "B.45")
    assert pset.hyperlink_001 == f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id=BDHH_6434B1"
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung B.45 (ID: BDHH_6434B1)"


def test_build_borehole_hyperlink_without_designation() -> None:
    pset = build_borehole_hyperlink("BDHH_6434B1")
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung (ID: BDHH_6434B1)"


def test_build_borehole_hyperlink_accepts_numeric_portal_id() -> None:
    """The portal expects the numeric Archivnummer, which BoreholeML omits."""
    pset = build_borehole_hyperlink("BDHH_6434B1", "B.IX/182", portal_id="44381")
    assert pset.hyperlink_001 == f"{BOREHOLE_PORTAL_URL}?sid={BOREHOLE_PORTAL_SID}&id=44381"
    assert pset.hyperlink_001_bemerkung == "Link zur Bohrung B.IX/182 (ID: 44381)"


def test_parsed_record_carries_portal_hyperlink() -> None:
    xml = _borehole_xml(intervals=_interval(from_depth="0.0", to_depth="2.5", rock_code="mS"))
    record = records_from_boreholeml(xml)[0]
    hyperlink = record.psets["Pset_Hyperlink"]
    assert isinstance(hyperlink, Pset_Hyperlink)
    assert hyperlink.hyperlink_001.endswith("&id=BDHH_TEST1")
    assert BOREHOLE_PORTAL_SID in hyperlink.hyperlink_001


def test_serialized_pset_uses_bimhh_aliases() -> None:
    dumped = Pset_Aufschlussbereich(bodenart="mS (Mittelsand)").model_dump(by_alias=True)
    assert dumped["_Bodenart"] == "mS (Mittelsand)"


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
        easting=565084.16,
        northing=5934034.654,
        ansatzhoehe_nn=14.3,
    )
    assert BoreholesGenericApp.build_ifc([record], request_params=request_params) is None
