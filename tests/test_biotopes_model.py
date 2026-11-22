import pytest
from pydantic import BaseModel, ValidationError

from BIMFabrikHH_core.core.ogc_extractor.geojson import PolygonRings
from BIMFabrikHH_core.data_models.biotopes import (
    BiotopeRecord,
    BiotopeShape,
    _combine_haupt_and_neben_biotopes,
    _record_with_psets_from_payload,
    build_biotope_hyperlink,
    collect_biotope_psets,
    load_biotope_hh_descriptions_mapping,
    map_biotope_type_bkompv_codes,
    map_biotope_type_hh_descriptions,
    records_from_geojson_feature_collection,
)
from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import Pset_Objektinformation_Biotop


@pytest.fixture
def biotope_record():
    return BiotopeRecord(
        feature_id=123,
        shape_type=BiotopeShape.AREA,
        polygons=[PolygonRings(exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], holes=[])],
        lines=None,
        point=None,
        objectid=1,
        id_biotop=1001,
        dk5=1234,
        biotop_nr=5,
        abschnitt=1,
        is_protected=True,
        hauptbiotoptyp="NRT",
        nebenbiotoptypen="",
        naechste_kartierung=None,
    )


@pytest.mark.unit
def test_biotope_record_creation(biotope_record: BiotopeRecord):
    assert biotope_record.feature_id == 123
    assert biotope_record.shape_type == BiotopeShape.AREA
    assert biotope_record.is_protected is True


@pytest.mark.unit
def test_biotope_record_requires_feature_id():
    with pytest.raises(ValidationError):
        BiotopeRecord(
            shape_type=BiotopeShape.AREA,
            polygons=[],
            lines=None,
            point=None,
            objectid=1,
            id_biotop=1001,
            dk5=1234,
            biotop_nr=5,
            abschnitt=1,
            is_protected=True,
            naechste_kartierung=None,
        )


@pytest.mark.unit
def test_biotope_record_requires_shape_type():
    with pytest.raises(ValidationError):
        BiotopeRecord(
            feature_id=123,
            polygons=[],
            objectid=1,
            id_biotop=1001,
            dk5=1234,
            biotop_nr=5,
            is_protected=True,
        )


@pytest.mark.unit
def test_biotope_record_requires_is_protected(biotope_record: BiotopeRecord):
    with pytest.raises(ValidationError):
        BiotopeRecord.model_validate(biotope_record.model_dump(exclude={"psets", "is_protected"}))


@pytest.mark.unit
def test_naechste_kartierung_defaults_to_none(biotope_record: BiotopeRecord):
    record = BiotopeRecord.model_validate(biotope_record.model_dump(exclude={"psets", "naechste_kartierung"}))

    assert record.naechste_kartierung is None


@pytest.mark.unit
@pytest.mark.parametrize("point", [(), (1.0,), ("a", "b")])
def test_point_must_be_two_coordinates(biotope_record: BiotopeRecord, point):
    payload = {**biotope_record.model_dump(exclude={"psets"}), "shape_type": BiotopeShape.POINT, "point": point}

    with pytest.raises(ValidationError):
        BiotopeRecord.model_validate(payload)


def _feature_collection(geometry, **properties):
    feature = {
        "type": "Feature",
        "id": 7,
        "geometry": geometry,
        "properties": {"objectid": 1, "id_biotop": 1001, "dk5": 1234, "biotop_nr": 5, **properties},
    }
    return {"type": "FeatureCollection", "features": [feature]}


_POINT = {"type": "Point", "coordinates": [565000.0, 5935000.0]}


@pytest.mark.unit
@pytest.mark.parametrize(
    "geometry",
    [
        {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]},
        {"type": "MultiPoint", "coordinates": [[0.0, 0.0]]},
        None,
    ],
)
def test_unsupported_geometry_is_skipped_with_warning(geometry, caplog):
    records = records_from_geojson_feature_collection(_feature_collection(geometry), is_protected=True)

    assert records == []
    assert "Skipping biotope feature 7" in caplog.text


@pytest.mark.unit
@pytest.mark.parametrize(
    ("properties", "expected"),
    [
        ({"paragraf": "§ 30 (2) 1.2 Natürliche Stillgewässer"}, True),
        ({"paragraf": ""}, False),
        ({}, False),
    ],
)
def test_is_protected_from_paragraf_value(properties, expected):
    (record,) = records_from_geojson_feature_collection(_feature_collection(_POINT, **properties), is_protected=None)

    assert record.is_protected is expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("shape", "expected"),
    [
        (BiotopeShape.AREA, "Biotop_Flaeche_1001_Abschnitt_1"),
        (BiotopeShape.LINES, "Biotop_Linie_1001_Abschnitt_1"),
        (BiotopeShape.POINT, "Biotop_Punkt_1001_Abschnitt_1"),
    ],
)
def test_element_name(biotope_record: BiotopeRecord, shape, expected):
    biotope_record.shape_type = shape
    assert biotope_record.element_name == expected


@pytest.mark.unit
def test_element_name_differs_per_abschnitt(biotope_record: BiotopeRecord):
    second_section = biotope_record.model_copy(update={"abschnitt": 2})

    assert biotope_record.element_name == "Biotop_Flaeche_1001_Abschnitt_1"
    assert second_section.element_name == "Biotop_Flaeche_1001_Abschnitt_2"


@pytest.mark.unit
def test_element_name_without_abschnitt(biotope_record: BiotopeRecord):
    biotope_record.abschnitt = None

    assert biotope_record.element_name == "Biotop_Flaeche_1001"


def test_element_color_is_stable_and_rgb(biotope_record: BiotopeRecord):
    record_a = biotope_record.model_copy()
    record_a.hauptbiotoptyp = "ABC"

    record_b = biotope_record.model_copy()
    record_b.hauptbiotoptyp = "ABC"

    record_c = biotope_record.model_copy()
    record_c.hauptbiotoptyp = "DEF"

    assert record_a.element_color == record_b.element_color
    assert record_a.element_color != record_c.element_color
    assert len(record_a.element_color) == 3
    assert all(0 <= channel <= 255 for channel in record_a.element_color)


class DummyPset(BaseModel):
    value: str = "test"


@pytest.mark.unit
def test_collect_biotope_psets(biotope_record: BiotopeRecord):
    pset = DummyPset()

    biotope_record.psets = {"DummyPset": pset}

    result = collect_biotope_psets(biotope_record)

    assert result == [pset]


@pytest.mark.unit
def test_collect_biotope_psets_disabled(biotope_record: BiotopeRecord):
    biotope_record.psets = {"DummyPset": DummyPset()}

    assert (
        collect_biotope_psets(
            biotope_record,
            include_property_sets=False,
        )
        == []
    )


@pytest.mark.unit
def test_collect_biotope_psets_empty(biotope_record: BiotopeRecord):
    biotope_record.psets = {}

    assert collect_biotope_psets(biotope_record) == []


@pytest.mark.unit
def test_collect_biotope_psets_skips_invalid_values(biotope_record: BiotopeRecord):
    biotope_record.psets = {
        "valid": DummyPset(),
        "invalid": {"value": "not a model"},
    }

    result = collect_biotope_psets(biotope_record)

    assert len(result) == 1
    assert isinstance(result[0], DummyPset)


def _objektinfo_pset(record: BiotopeRecord, **changes):
    payload = {**record.model_dump(exclude={"psets"}), **changes}
    return _record_with_psets_from_payload(payload, biotope_name_mapping={}).psets[
        Pset_Objektinformation_Biotop.pset_name
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("is_protected", "schutzstatus_teilweise", "expected"),
    [
        (False, None, "nicht geschützt"),
        (True, "Ja", "teilweise geschützt"),
        (True, None, "vollständig geschützt"),
    ],
)
def test_protection_status_landesrecht(biotope_record: BiotopeRecord, is_protected, schutzstatus_teilweise, expected):
    pset = _objektinfo_pset(biotope_record, is_protected=is_protected, schutzstatus_teilweise=schutzstatus_teilweise)

    assert pset.ist_gesetzl_gesch_biotop_landesrecht == expected


@pytest.mark.unit
def test_gesamtwert_from_gesamtbewertung(biotope_record: BiotopeRecord):
    pset = _objektinfo_pset(biotope_record, gesamtbewertung=6)

    assert pset.biotop_gesamtwert == "6"
    assert pset.biotop_gesamtwert_bedeutung == "wertvoll"


@pytest.mark.unit
def test_gesamtwert_without_gesamtbewertung_is_undefined(biotope_record: BiotopeRecord):
    pset = _objektinfo_pset(biotope_record, gesamtbewertung=None)

    assert pset.biotop_gesamtwert == "undefiniert"
    assert pset.biotop_gesamtwert_bedeutung == "undefiniert"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("97.505", 97505.0),
        ("137.832", 137832.0),
        ("953", 953.0),
        (953, 953.0),
        (None, None),
    ],
)
def test_flaeche_oder_laenge_parses_german_thousands(biotope_record: BiotopeRecord, raw, expected):
    payload = {**biotope_record.model_dump(exclude={"psets"}), "flaeche_oder_laenge": raw}

    assert BiotopeRecord.model_validate(payload).flaeche_oder_laenge == expected


@pytest.mark.unit
def test_groesse_ha_for_area_biotope(biotope_record: BiotopeRecord):
    pset = _objektinfo_pset(biotope_record, flaeche_oder_laenge=97505.0)

    assert pset.biotop_groesse_ha == pytest.approx(9.7505)


@pytest.mark.unit
@pytest.mark.parametrize("shape", [BiotopeShape.LINES, BiotopeShape.POINT])
def test_groesse_ha_only_for_area_biotopes(biotope_record: BiotopeRecord, shape):
    pset = _objektinfo_pset(biotope_record, shape_type=shape, flaeche_oder_laenge=953.0)

    assert pset.biotop_groesse_ha is None


@pytest.mark.unit
def test_combine_haupt_and_neben_biotopes():
    assert _combine_haupt_and_neben_biotopes("NRT", ["NRT", "WRT", "WRT"]) == "NRT (NRT; WRT)"


@pytest.mark.unit
def test_combine_biotopes_without_secondary_types():
    assert _combine_haupt_and_neben_biotopes("NRT", []) == "NRT"


@pytest.mark.unit
def test_combine_biotopes_without_primary_type():
    assert _combine_haupt_and_neben_biotopes("", ["NRT"]) == ""


@pytest.mark.unit
@pytest.mark.parametrize(
    ("nebenbiotoptypen", "expected_code", "expected_name"),
    [
        ("", "NRT", "Schilf-Röhricht der Tide-Elbe"),
        ("SEN, ", "NRT (SEN)", "Schilf-Röhricht der Tide-Elbe (Natürliches, nährstoffreiches Stillgewässer)"),
    ],
)
def test_empty_nebenbiotoptyp_codes_are_dropped(
    biotope_record: BiotopeRecord, nebenbiotoptypen, expected_code, expected_name
):
    payload = {**biotope_record.model_dump(exclude={"psets"}), "nebenbiotoptypen": nebenbiotoptypen}
    pset = _record_with_psets_from_payload(payload, load_biotope_hh_descriptions_mapping()).psets[
        Pset_Objektinformation_Biotop.pset_name
    ]

    assert pset.biotoptyp_land_code == expected_code
    assert pset.biotoptyp_land_name == expected_name


@pytest.mark.unit
def test_hh_descriptions_have_no_empty_code():
    assert "" not in load_biotope_hh_descriptions_mapping()


@pytest.mark.unit
def test_build_biotope_hyperlink():
    result = build_biotope_hyperlink(
        "https://example.com/biotope/1001",
        1001,
    )
    assert result.hyperlink_001 == "https://example.com/biotope/1001"
    assert "1001" in result.hyperlink_001_bemerkung


@pytest.mark.unit
def test_build_biotope_hyperlink_without_url():
    result = build_biotope_hyperlink("", 1001)

    assert result.hyperlink_001 == ""
    assert "Kein Erhebungsbogen verfügbar" in result.hyperlink_001_bemerkung


@pytest.mark.unit
def test_map_hh_biotope_description():
    result = map_biotope_type_hh_descriptions(
        "NRT",
        {"NRT": "Schilf-Röhricht"},
    )

    assert result == "Schilf-Röhricht"


@pytest.mark.unit
def test_map_biotope_description_unknown_code():
    assert (
        map_biotope_type_hh_descriptions(
            "UNKNOWN",
            {"NRT": "Schilf-Röhricht"},
        )
        == ""
    )


@pytest.mark.unit
@pytest.mark.parametrize(("code", "expected"), [(" NRT ", "Schilf-Röhricht"), (None, "")])
def test_map_hh_biotope_description_trims_code(code, expected):
    assert map_biotope_type_hh_descriptions(code, {"NRT": "Schilf-Röhricht"}) == expected


@pytest.mark.unit
def test_map_bkompv_code():
    assert (
        map_biotope_type_bkompv_codes(
            "NRT",
            {"NRT": "38.02.01"},
        )
        == "38.02.01"
    )
