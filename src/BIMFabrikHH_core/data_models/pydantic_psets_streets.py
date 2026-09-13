"""``Pset_Objektinformation`` template for ALKIS Nutzung traffic surfaces."""

from __future__ import annotations

from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, ConfigDict, Field


class Pset_Objektinformation_Strasse(PropertySetTemplate):
    """Property set mirroring ALKIS ``Nutzung`` fields for traffic surfaces."""

    model_config = ConfigDict(populate_by_name=True)

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Verkehr",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Strassenverkehr",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Strasse",
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=300,
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="ALKIS Tatsaechliche Nutzung (Strassenverkehr / Weg / Bahnverkehr)",
    )
    nutzart: str = Field(
        validation_alias=AliasChoices("nutzart", "_Nutzart"),
        serialization_alias="_Nutzart",
        default="",
    )
    bez: str = Field(
        validation_alias=AliasChoices("bez", "_Bez"),
        serialization_alias="_Bez",
        default="",
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "_Name"),
        serialization_alias="_Name",
        default="",
    )
    oid: str = Field(
        validation_alias=AliasChoices("oid", "_Oid"),
        serialization_alias="_Oid",
        default="",
    )
    aktualit: Optional[str] = Field(
        validation_alias=AliasChoices("aktualit", "_Aktualit"),
        serialization_alias="_Aktualit",
        default=None,
    )


__all__ = [
    "Pset_Objektinformation_Strasse",
]
