import pytest

from BIMFabrikHH_core.data_models.flurstuecke import (
    FlurstueckRecord,
    collect_flurstueck_psets,
    records_from_geojson_feature_collection,
)
from BIMFabrikHH_core.data_models.pydantic_psets_flurstuecke import Pset_Objektinformation_Flurstueck


def square(x0=0, y0=0, x1=10, y1=10):
    return [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
    ]


def parcel_feature(
    *,
    feature_id=123,
    geometry_type="MultiPolygon",
    coordinates=None,
    properties=None,
):
    if coordinates is None:
        if geometry_type == "MultiPolygon":
            coordinates = [[square()]]
        else:
            coordinates = [square()]

    return {
        "type": "Feature",
        "id": feature_id,
        "properties": properties or {},
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates,
        },
    }


@pytest.mark.unit
def test_parses_parcel_attributes_and_creates_pset():
    properties = {
        "idflurst": "DEHHALKA01234abc",
        "flaeche": 100.0,
        "flstkennz": "123456___78901______",
        "gemarkung": "Altstadt Nord",
        "gemaschl": "012345",
        "flstnrzae": "42",
        "aktualit": "2022-01-31Z",
        "lagebeztxt": "Musterstraße",
        "tntxt": "Wohnbaufläche;100",
    }

    records = records_from_geojson_feature_collection(
        {
            "type": "FeatureCollection",
            "features": [parcel_feature(properties=properties)],
        }
    )

    assert len(records) == 1
    record = records[0]

    assert record.feature_id == 123
    assert record.idflurst == properties["idflurst"]
    assert record.flaeche == pytest.approx(properties["flaeche"])
    assert record.flstkennz == properties["flstkennz"]
    assert record.gemarkung == properties["gemarkung"]
    assert record.gemaschl == properties["gemaschl"]
    assert record.flstnrzae == properties["flstnrzae"]
    assert record.aktualit == properties["aktualit"]
    assert record.lagebeztxt == properties["lagebeztxt"]
    assert record.tntxt == properties["tntxt"]
    assert record.geometry_crs == "EPSG:25832"

    assert len(record.polygons) == 1
    assert len(record.psets) == 1

    pset = record.psets["Pset_Objektinformation"]
    assert isinstance(pset, Pset_Objektinformation_Flurstueck)
    assert pset.bemerkung == "Altstadt Nord; Musterstraße"
    assert pset.alkisidentifikator == properties["idflurst"]
    assert pset.amtlicheflaeche.magnitude == pytest.approx(properties["flaeche"])
    assert pset.flurstueckkennzeichen == properties["flstkennz"]
    assert pset.gemarkungname == properties["gemarkung"]
    assert pset.lzibeginnt == "2022-01-31"


@pytest.mark.unit
def test_skips_features_without_polygon_geometry():
    data = {
        "type": "FeatureCollection",
        "features": [
            parcel_feature(
                feature_id=1,
                geometry_type="Point",
                coordinates=[1, 2],
            ),
            parcel_feature(feature_id=2),
        ],
    }

    records = records_from_geojson_feature_collection(data)

    assert len(records) == 1
    assert records[0].feature_id == 2


@pytest.mark.unit
def test_missing_properties_are_skipped():
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": 1,
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[square()]],
                },
            }
        ],
    }

    assert records_from_geojson_feature_collection(data) == []


@pytest.mark.unit
def test_empty_properties_are_not_skipped():
    data = {
        "type": "FeatureCollection",
        "features": [
            parcel_feature(
                feature_id=123,
                geometry_type="MultiPolygon",
                coordinates=[[square()]],
                properties={},
            ),
        ],
    }

    records = records_from_geojson_feature_collection(data)

    assert len(records) == 1

    record = records[0]
    assert record.feature_id == 123
    assert record.idflurst == ""
    assert record.flaeche is None
    assert record.gemarkung == ""
    assert record.flstnrzae == ""
    assert len(record.polygons) == 1
    assert len(record.psets) == 1

    pset = record.psets["Pset_Objektinformation"]
    assert isinstance(pset, Pset_Objektinformation_Flurstueck)
    assert pset.bemerkung == "undefiniert"
    assert pset.alkisidentifikator == ""
    assert pset.amtlicheflaeche is None
    assert pset.flurstueckkennzeichen == ""
    assert pset.gemarkungname == ""
    assert pset.lzibeginnt == "undefiniert"


@pytest.mark.unit
def test_missing_feature_id_uses_deterministic_fallback():
    records = records_from_geojson_feature_collection(
        {
            "type": "FeatureCollection",
            "features": [
                parcel_feature(feature_id=None),
            ],
        }
    )

    assert records[0].feature_id == "feature_0"


@pytest.mark.unit
def test_multiple_missing_feature_ids_are_distinct():
    records = records_from_geojson_feature_collection(
        {
            "type": "FeatureCollection",
            "features": [parcel_feature(feature_id=None), parcel_feature(feature_id=None)],
        }
    )

    assert records[0].feature_id != records[1].feature_id


@pytest.mark.unit
def test_geometry_crs_is_preserved():
    data = {
        "type": "FeatureCollection",
        "features": [parcel_feature()],
    }

    default_record = records_from_geojson_feature_collection(data)[0]
    geographic_record = records_from_geojson_feature_collection(data, geometry_crs="EPSG:4326")[0]

    assert default_record.geometry_crs == "EPSG:25832"
    assert geographic_record.geometry_crs == "EPSG:4326"


@pytest.mark.unit
def test_element_name_uses_gemarkung_and_parcel_number():
    record = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        gemarkung="Hamburg Mitte",
        flstnrzae="12345",
    )

    assert record.element_name == "Flurstueck_Hamburg_Mitte_12345"


@pytest.mark.unit
def test_element_name_falls_back_to_kennzeichen_then_feature_id():
    with_kennzeichen = FlurstueckRecord(
        feature_id=7,
        polygons=[],
        flstkennz="123456___78901______",
    )
    without_kennzeichen = FlurstueckRecord(
        feature_id=7,
        polygons=[],
    )

    assert with_kennzeichen.element_name == "Flurstueck_123456___78901______"
    assert without_kennzeichen.element_name == "Flurstueck_7"


@pytest.mark.unit
def test_element_bemerkung_uses_undefined_for_missing_location():
    record = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        gemarkung="Hamburg",
    )

    assert record.element_bemerkung == "Hamburg; undefiniert"


@pytest.mark.unit
def test_element_lzibeginnt_normalizes_timestamp_suffix():
    record = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        aktualit="2026-12-31T12:30:00Z",
    )

    assert record.element_lzibeginnt == "2026-12-31"


@pytest.mark.unit
def test_element_color_is_stable_and_rgb():
    record_a = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        gemarkung="Hamburg Mitte",
    )

    record_b = FlurstueckRecord(
        feature_id=2,
        polygons=[],
        gemarkung="Hamburg Mitte",
    )

    record_c = FlurstueckRecord(
        feature_id=2,
        polygons=[],
        gemarkung="Hamburg Nord",
    )

    assert record_a.element_color == record_b.element_color
    assert record_a.element_color != record_c.element_color
    assert len(record_a.element_color) == 3
    assert all(0 <= channel <= 255 for channel in record_a.element_color)


@pytest.mark.unit
def test_collect_psets_returns_models():
    pset = Pset_Objektinformation_Flurstueck()
    record = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        psets={"Pset_Objektinformation": pset},
    )

    assert collect_flurstueck_psets(record) == [pset]


@pytest.mark.unit
def test_collect_psets_can_be_disabled():
    record = FlurstueckRecord(
        feature_id=1,
        polygons=[],
        psets={"Pset_Objektinformation": Pset_Objektinformation_Flurstueck()},
    )

    assert collect_flurstueck_psets(record, include_property_sets=False) == []
