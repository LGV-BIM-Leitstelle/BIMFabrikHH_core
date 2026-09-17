"""Property set templates for Wasser (water) IFC elements.
"""

from __future__ import annotations

from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field

from BIMFabrikHH_core.apps.boreholes.helper import UNDEFINED


class Pset_Objektinformation_Water(PropertySetTemplate):
    """``Pset_Objektinformation`` variant for Wasser elements."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Wasser",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Grundwasser",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Grundwasser",
    )
    log: int = Field(
        validation_alias=AliasChoices("log", "_LOG"),
        serialization_alias="_LOG",
        default=100,
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LOI"),
        serialization_alias="_LOI",
        default=200,
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="Baugrundaufschluss Hamburg (WFS BoreholeML 3.0)",
    )


class Pset_Schicht_Water(PropertySetTemplate):
    """Layer-level geotechnical classification."""

    pset_name: ClassVar[str] = "Pset_Schicht"

    schichtnummer: str = Field(
        validation_alias=AliasChoices("schichtnummer", "_Schichtnummer"),
        serialization_alias="_Schichtnummer",
        default=UNDEFINED,
    )


class Pset_Wasser_Water(PropertySetTemplate):
    """Groundwater depth."""

    pset_name: ClassVar[str] = "Pset_Wasser"

    wasserstandhoehe: float = Field(
        validation_alias=AliasChoices("wasserstandhoehe", "_WasserstandHoehe", "wasserstand"),
        serialization_alias="_WasserstandHoehe",
        default=UNDEFINED,
    )



__all__ = [
    "Pset_Objektinformation_Water",
    "Pset_Schicht_Water",
    "Pset_Wasser_Water",
]
