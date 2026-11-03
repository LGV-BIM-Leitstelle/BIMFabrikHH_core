import pytest
from pydantic import ValidationError

from BIMFabrikHH_core.data_models.pydantic_psets_biotopes import (
    Pset_Objektinformation_Biotop,
    Pset_Objektinformation_Lebensraum,
)


def test_lebensraum_pset_defaults():
    pset = Pset_Objektinformation_Lebensraum()

    assert pset.idebene1 == "Lebensraum"
    assert pset.log == 100
    assert pset.loi == 300
    assert pset.kartierung_jahr == "undefiniert"
    assert pset.kartierer == "undefiniert"
    assert pset.erhebungsmethode == "undefiniert"
    assert pset.bemerkung == "undefiniert"
    assert pset.ist_ffh_lebensraum is False


def test_lebensraum_pset_aliases():
    pset = Pset_Objektinformation_Lebensraum(
        _IDEbene1="Test",
        _LoG=200,
        _LoI=400,
        _KartierungJahr="2023",
        _Kartierer="Klaus",
        _Erhebungsmethode="Drohne",
        _Bemerkung="test",
        _IstFFHLebensraum=True,
    )

    assert pset.idebene1 == "Test"
    assert pset.log == 200
    assert pset.loi == 400
    assert pset.kartierung_jahr == "2023"
    assert pset.erhebungsmethode == "Drohne"
    assert pset.bemerkung == "test"
    assert pset.ist_ffh_lebensraum == True


def test_biotop_pset_required_fields():
    with pytest.raises(ValidationError):
        Pset_Objektinformation_Biotop()


def test_biotop_pset_creation():
    pset = Pset_Objektinformation_Biotop(
        biotopnummer=1001,
        ist_gesetzl_gesch_biotop=True,
    )

    assert pset.biotop_nr == 1001
    assert pset.ist_gesetzl_gesch_biotop is True


def test_biotop_pset_inherits_lebensraum_fields():
    pset = Pset_Objektinformation_Biotop(
        biotopnummer=1001,
        ist_gesetzl_gesch_biotop=False,
    )

    assert pset.idebene1 == "Lebensraum"
    assert pset.idebene2 == "Biotop"
    assert pset.idebene3 == "Biotop"
    assert pset.log == 100
    assert pset.loi == 300


def test_biotop_pset_default_values():
    pset = Pset_Objektinformation_Biotop(
        biotopnummer=1001,
        ist_gesetzl_gesch_biotop=False,
    )

    assert pset.abschnitt_nr == 1
    assert pset.biotoptyp_bkompv_code == "undefiniert"
    assert pset.biotoptyp_bkompv_name == "undefiniert"
    assert pset.biotoptyp_land_code == "undefiniert"
    assert pset.biotoptyp_land_name == "undefiniert"
    assert pset.biotop_gesamtwert == "undefiniert"
    assert pset.biotop_gesamtwert_liste == "undefiniert"
    assert pset.biotop_gesamtwert_bedeutung == "undefiniert"
    assert pset.gefaehrdung_status == "undefiniert"
    assert pset.ist_gesetzl_gesch_biotop_landesrecht == "undefiniert"
    assert pset.biotop_groesse_ha is None


def test_biotop_pset_serialization_aliases():
    pset = Pset_Objektinformation_Biotop(
        biotopnummer=1001,
        ist_gesetzl_gesch_biotop=True,
    )

    data = pset.model_dump(by_alias=True)

    assert data["_Biotopnummer"] == 1001
    assert data["_IDEbene1"] == "Lebensraum"
    assert data["_IDEbene2"] == "Biotop"
    assert data["_IstGesetzlgeschBiotop"] is True


def test_biotop_pset_accepts_serialization_aliases():
    pset = Pset_Objektinformation_Biotop(
        _Biotopnummer=1001,
        _IstGesetzlgeschBiotop=True,
    )

    assert pset.biotop_nr == 1001
    assert pset.ist_gesetzl_gesch_biotop is True


def test_biotop_pset_accepts_alternative_field_names():
    pset = Pset_Objektinformation_Biotop(
        biotopnummer=1001,
        biotopabschnittnummer=3,
        ist_gesetzl_gesch_biotop=True,
    )

    assert pset.biotop_nr == 1001
    assert pset.abschnitt_nr == 3
