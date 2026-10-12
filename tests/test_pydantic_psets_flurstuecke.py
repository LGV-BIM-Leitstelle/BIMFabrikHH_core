import pytest

from BIMFabrikHH_core.data_models.pydantic_psets_flurstuecke import \
    Pset_Objektinformation_Flurstueck


@pytest.mark.unit
def test_default_pset_objektinformation_flurstueck():
    pset = Pset_Objektinformation_Flurstueck()

    assert pset.idebene1 == "Flurstueck"
    assert pset.idebene2 == "Flurstueck"
    assert pset.idebene3 == "Flurstueck"
    assert pset.log == 100
    assert pset.loi == 300
    assert pset.bemerkung == "undefiniert"
    assert pset.alkisidentifikator == ""
    assert pset.amtlicheflaeche == None
    assert pset.flurstueckkennzeichen == ""
    assert pset.gemarkungname == ""
    assert pset.lzibeginnt == "undefiniert"


@pytest.mark.unit
def test_accepts_python_field_names():
    pset = Pset_Objektinformation_Flurstueck(
        alkisidentifikator="ALKIS-123",
        flurstueckkennzeichen="PARCEL-123",
        gemarkungname="Hamburg",
        bemerkung="Hamburg; Musterstraße",
        lzibeginnt="2025-01-31",
    )

    assert pset.alkisidentifikator == "ALKIS-123"
    assert pset.flurstueckkennzeichen == "PARCEL-123"
    assert pset.gemarkungname == "Hamburg"
    assert pset.bemerkung == "Hamburg; Musterstraße"


@pytest.mark.unit
def test_accepts_ifc_serialization_aliases():
    pset = Pset_Objektinformation_Flurstueck.model_validate(
        {
            "_IDEbene1": "Flurstueck",
            "_LoG": 100,
            "_LoI": 300,
            "_Bemerkung": "Hamburg; Musterstraße",
            "_ALKISIdentifikator": "ALKIS-123",
            "_Flurstueckkennzeichen": "PARCEL-123",
            "_GemarkungName": "Hamburg",
            "_LZIbeginnt": "2025-01-31",
        }
    )

    assert pset.alkisidentifikator == "ALKIS-123"
    assert pset.flurstueckkennzeichen == "PARCEL-123"
    assert pset.gemarkungname == "Hamburg"
    assert pset.bemerkung == "Hamburg; Musterstraße"


@pytest.mark.unit
def test_serialization_uses_ifc_property_names():
    pset = Pset_Objektinformation_Flurstueck(
        alkisidentifikator="ALKIS-123",
        flurstueckkennzeichen="PARCEL-123",
        gemarkungname="Hamburg",
    )

    data = pset.model_dump(by_alias=True)

    assert data["_IDEbene1"] == "Flurstueck"
    assert data["_IDEbene2"] == "Flurstueck"
    assert data["_IDEbene3"] == "Flurstueck"
    assert data["_LoG"] == 100
    assert data["_LoI"] == 300
    assert data["_ALKISIdentifikator"] == "ALKIS-123"
    assert data["_Flurstueckkennzeichen"] == "PARCEL-123"
    assert data["_GemarkungName"] == "Hamburg"
    assert data["_LZIbeginnt"] == "undefiniert"


@pytest.mark.unit
def test_official_area_is_optional():
    pset = Pset_Objektinformation_Flurstueck()

    assert pset.amtlicheflaeche is None


@pytest.mark.unit
def test_all_expected_properties_are_declared():
    fields = Pset_Objektinformation_Flurstueck.model_fields

    assert set(fields) == {
        "idebene1",
        "idebene2",
        "idebene3",
        "log",
        "loi",
        "bemerkung",
        "alkisidentifikator",
        "amtlicheflaeche",
        "flurstueckkennzeichen",
        "gemarkungname",
        "lzibeginnt",
    }
