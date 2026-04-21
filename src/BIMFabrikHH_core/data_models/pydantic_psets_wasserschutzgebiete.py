"""``Pset_Objektinformation`` template for Wasserschutzgebiet IFC elements."""

from __future__ import annotations

from typing import ClassVar

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Pset_Objektinformation_Wasserschutzgebiet(PropertySetTemplate):
    """Property set mirroring Hamburg API fields for Wasserschutzgebiete."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Umwelt",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Wasserschutzgebiet",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Wasserschutzgebiet",
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=300,
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="Wasserschutzgebiet Hamburg (OGC API Features)",
    )
    wsg: str = Field(
        validation_alias=AliasChoices("wsg", "_Wsg"),
        serialization_alias="_Wsg",
        default="",
    )
    gebietsname: str = Field(
        validation_alias=AliasChoices("gebietsname", "_Gebietsname"),
        serialization_alias="_Gebietsname",
        default="",
    )
    schutzzone: str = Field(
        validation_alias=AliasChoices("schutzzone", "_Schutzzone"),
        serialization_alias="_Schutzzone",
        default="",
    )
    rechtsgrundlage: str = Field(
        validation_alias=AliasChoices("rechtsgrundlage", "_Rechtsgrundlage"),
        serialization_alias="_Rechtsgrundlage",
        default="",
    )
    erfassungsgrundlage: str = Field(
        validation_alias=AliasChoices("erfassungsgrundlage", "_Erfassungsgrundlage"),
        serialization_alias="_Erfassungsgrundlage",
        default="",
    )
    ausweisung: str = Field(
        validation_alias=AliasChoices("ausweisung", "_Ausweisung"),
        serialization_alias="_Ausweisung",
        default="",
    )
    bearbeitungsstand: str = Field(
        validation_alias=AliasChoices("bearbeitungsstand", "_Bearbeitungsstand"),
        serialization_alias="_Bearbeitungsstand",
        default="",
    )
    info_kontakt: str = Field(
        validation_alias=AliasChoices("info_kontakt", "_InfoKontakt"),
        serialization_alias="_InfoKontakt",
        default="",
    )
    info: str = Field(
        validation_alias=AliasChoices("info", "_Info"),
        serialization_alias="_Info",
        default="",
    )
    idherkunft: int = Field(
        validation_alias=AliasChoices("idherkunft", "_IDHerkunft"),
        serialization_alias="_IDHerkunft",
        default=0,
    )


__all__ = [
    "Pset_Objektinformation_Wasserschutzgebiet",
]
