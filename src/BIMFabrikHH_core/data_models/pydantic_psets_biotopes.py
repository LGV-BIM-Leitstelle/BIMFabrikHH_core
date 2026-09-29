"""``Pset_Objektinformation`` template for Biotopkataster biotope IFC elements.

TODO: add description
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from ifcfactory import PropertySetTemplate
from ifcfactory._internal.pset_base import Quantity
from pydantic import AliasChoices, Field

# ``ifcfactory._internal.pset_base`` only ships ``Length`` / ``Time``; area maps
# to ``IfcAreaMeasure`` via ``pint_to_ifc[Dim("[length]") ** 2]``.
Area = Literal["[length]**2"]

UNDEFINED = "undefiniert"

class Pset_Objektinformation_Biotop(PropertySetTemplate):
    """Property set for one Biotopkataster biotope, per Merkmalsgruppe TODO."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Biotop",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Biotop",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Biotop",
    )
    log: int = Field(
        validation_alias=AliasChoices("log", "_LoG"),
        serialization_alias="_LoG",
        default=100,
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=300,
    )
    biotop_nr: int = Field(
        validation_alias=AliasChoices("biotop_nr", "biotopnummer",  "_Biotopnummer", "_BiotopNummer"),
        serialization_alias="_Biotopnummer"
    )
    abschnitt_nr: int = Field(
        validation_alias=AliasChoices("abschnitt_nr", "biotopabschnittnummer",  "_BiotopAbschnittnummer"),
        serialization_alias="_BiotopAbschnittnummer",
        default=1,
    )
    biotoptyp_land_code: str = Field(
        validation_alias=AliasChoices("biotoptyp_land_code", "_BiotoptypLandCode"),
        serialization_alias="_BiotoptypLandCode",
        default=UNDEFINED,
    )
    biotoptyp_land_name: str = Field(
        validation_alias=AliasChoices("biotoptyp_land_name", "_BiotoptypLandName"),
        serialization_alias="_BiotoptypLandName",
        default=UNDEFINED,
    )
    biotop_gesamtwert: str = Field(
        validation_alias=AliasChoices("biotop_gesamtwert", "_Biotopgesamtwert"),
        serialization_alias="_Biotopgesamtwert",
        default=UNDEFINED,
    )
    biotop_gesamtwert_liste: str = Field(
        validation_alias=AliasChoices("biotop_gesamtwert_liste", "_BiotopgesamtwertListe"),
        serialization_alias="_BiotopgesamtwertListe",
        default=UNDEFINED,
    )
    biotop_gesamtwert_bedeutung: str = Field(
        validation_alias=AliasChoices("biotop_gesamtwert_bedeutung", "_BiotopgesamtwertBedeutung"),
        serialization_alias="_BiotopgesamtwertBedeutung",
        default=UNDEFINED,
    )
    gefaehrdung_status: str = Field(
        validation_alias=AliasChoices("gefaerdung_status", "_GefaehrdungStatus"),
        serialization_alias="_GefaehrdungStatus",
        default=UNDEFINED,
    )
    ist_gesetzl_gesch_biotop: bool = Field(
        validation_alias=AliasChoices("ist_gesetzl_gesch_biotop", "_IstGesetzlgeschBiotop"),
        serialization_alias="_IstGesetzlgeschBiotop",
    )
    ist_gesetzl_gesch_biotop_landesrecht: str = Field(
        validation_alias=AliasChoices("ist_gesetzl_gesch_biotop_landesrecht", "_IstGesetzlgeschBiotopLandesrecht"),
        serialization_alias="_IstGesetzlgeschBiotopLandesrecht",
        default=UNDEFINED,
    )
    biotop_groesse_ha: Optional[Quantity[Area]] = Field(
        validation_alias=AliasChoices("biotop_groesse_ha", "_BiotopGroesse_ha"),
        serialization_alias="_BiotopGroesse_ha",
        default=None,
    )


__all__ = [
    "Area",
    "Pset_Objektinformation_Biotop",
]
