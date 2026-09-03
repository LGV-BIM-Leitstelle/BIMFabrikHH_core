"""Property set templates for Baugrundaufschluss (borehole) IFC elements.

``Pset_Aufschluss`` describes the borehole as a whole, the remaining three
describe a single layer (``Aufschlussbereich``), so a cylinder carries the
borehole pset plus its own layer psets.
"""

from __future__ import annotations

from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Pset_Aufschluss(PropertySetTemplate):
    """Borehole-level data (identical for every layer of one borehole)."""

    pset_name: ClassVar[str] = "Pset_Aufschluss"

    aufschlussart: str = Field(
        validation_alias=AliasChoices("aufschlussart", "_Aufschlussart"),
        serialization_alias="_Aufschlussart",
        default="undefiniert",
    )
    aufschlussdatum: str = Field(
        validation_alias=AliasChoices("aufschlussdatum", "_Aufschlussdatum", "bohrdatum"),
        serialization_alias="_Aufschlussdatum",
        default="undefiniert",
    )
    aufschlussnummer: str = Field(
        validation_alias=AliasChoices("aufschlussnummer", "_Aufschlussnummer", "aufschlussbezeichnung"),
        serialization_alias="_Aufschlussnummer",
        default="undefiniert",
    )
    hoehenansatzpunkt: Optional[float] = Field(
        validation_alias=AliasChoices("hoehenansatzpunkt", "_HoeheAnsatzpunkt", "ansatzhoehe_nn"),
        serialization_alias="_HoeheAnsatzpunkt",
        default=None,
    )
    laenge_baugrundaufschluss: Optional[float] = Field(
        validation_alias=AliasChoices("laenge_baugrundaufschluss", "_LaengeBaugrundaufschluss", "endteufe"),
        serialization_alias="_LaengeBaugrundaufschluss",
        default=None,
    )


class Pset_Aufschlussbereich(PropertySetTemplate):
    """Layer-level soil description (Bodenart, Farbe, Stratigraphie)."""

    pset_name: ClassVar[str] = "Pset_Aufschlussbereich"

    bodenart: str = Field(
        validation_alias=AliasChoices("bodenart", "_Bodenart", "hauptgemengteil"),
        serialization_alias="_Bodenart",
        default="undefiniert",
    )
    bodenart_ergaenzung: str = Field(
        validation_alias=AliasChoices("bodenart_ergaenzung", "_BodenartErgaenzung", "nebengemengteil"),
        serialization_alias="_BodenartErgaenzung",
        default="undefiniert",
    )
    bohrvorgang: str = Field(
        validation_alias=AliasChoices("bohrvorgang", "_Bohrvorgang"),
        serialization_alias="_Bohrvorgang",
        default="undefiniert",
    )
    farbe: str = Field(
        validation_alias=AliasChoices("farbe", "_Farbe"),
        serialization_alias="_Farbe",
        default="undefiniert",
    )
    kalkgehalt: str = Field(
        validation_alias=AliasChoices("kalkgehalt", "_Kalkgehalt"),
        serialization_alias="_Kalkgehalt",
        default="undefiniert",
    )
    stratigrapfie: str = Field(
        validation_alias=AliasChoices("stratigrapfie", "_Stratigrapfie", "stratigraphie"),
        serialization_alias="_Stratigrapfie",
        default="undefiniert",
    )


class Pset_Objektinformation_Borehole(PropertySetTemplate):
    """``Pset_Objektinformation`` variant for Baugrundaufschluss elements."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Baugrundaufschluss",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Aufschlussbereich",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Aufschlussbereich",
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


class Pset_Schicht(PropertySetTemplate):
    """Layer-level geotechnical classification."""

    pset_name: ClassVar[str] = "Pset_Schicht"

    bodengruppe: str = Field(
        validation_alias=AliasChoices("bodengruppe", "_Bodengruppe"),
        serialization_alias="_Bodengruppe",
        default="undefiniert",
    )
    bodenkonsistenz: str = Field(
        validation_alias=AliasChoices("bodenkonsistenz", "_Bodenkonsistenz", "konsistenz"),
        serialization_alias="_Bodenkonsistenz",
        default="undefiniert",
    )
    geologische_bezeichnung: str = Field(
        validation_alias=AliasChoices("geologische_bezeichnung", "_GeologischeBezeichnung"),
        serialization_alias="_GeologischeBezeichnung",
        default="undefiniert",
    )
    genese: str = Field(
        validation_alias=AliasChoices("genese", "_Genese"),
        serialization_alias="_Genese",
        default="undefiniert",
    )


__all__ = [
    "Pset_Aufschluss",
    "Pset_Aufschlussbereich",
    "Pset_Objektinformation_Borehole",
    "Pset_Schicht",
]
