import pytest
from pydantic import BaseModel, ValidationError

from BIMFabrikHH_core.core.ogc_extractor.geojson import PolygonRings
from BIMFabrikHH_core.data_models.biotopes import (
    BiotopeRecord,
    BiotopeShape,
    _combine_haupt_and_neben_biotopes,
    build_biotope_hyperlink,
    collect_biotope_psets,
    map_biotope_type_bkompv_codes,
    map_biotope_type_hh_descriptions,
)


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
@pytest.mark.parametrize(
    ("shape", "expected"),
    [
        (BiotopeShape.AREA, "Biotop_area_1001"),
        (BiotopeShape.LINES, "Biotop_lines_1001"),
        (BiotopeShape.POINT, "Biotop_point_1001"),
    ],
)
def test_element_name(biotope_record: BiotopeRecord, shape, expected):
    biotope_record.shape_type = shape
    assert biotope_record.element_name == expected


@pytest.mark.unit
def test_element_name_fallback_to_dk5_and_biotop_nr(biotope_record: BiotopeRecord):
    biotope_record.id_biotop = None

    assert biotope_record.element_name == "Biotop_area_1234_5"


@pytest.mark.unit
def test_element_name_fallback_to_feature_id(biotope_record: BiotopeRecord):
    biotope_record.id_biotop = None
    biotope_record.dk5 = None

    assert biotope_record.element_name == "Biotop_area_123"


@pytest.mark.unit
def test_element_name_max_length(biotope_record: BiotopeRecord):
    biotope_record.id_biotop = None
    biotope_record.dk5 = None
    biotope_record.feature_id = "x" * 200

    assert len(biotope_record.element_name) <= 120
    assert biotope_record.element_name[-1] == "x"


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
def test_map_bkompv_code():
    assert (
        map_biotope_type_bkompv_codes(
            "NRT",
            {"NRT": "38.02.01"},
        )
        == "38.02.01"
    )
