import datetime
from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Pset_Objektinformation(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Objektinformation"
    idebene1: str = Field(validation_alias=AliasChoices("idebene1", "_IDEbene1"), serialization_alias="_IDEbene1")
    idebene2: str = Field(validation_alias=AliasChoices("idebene2", "_IDEbene2"), serialization_alias="_IDEbene2")
    idebene3: str = Field(validation_alias=AliasChoices("idebene3", "_IDEbene3"), serialization_alias="_IDEbene3")


class Pset_Modellinformation(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Modellinformation"
    artfachmodell: str = Field(
        validation_alias=AliasChoices("artfachmodell", "_ArtFachmodell"),
        serialization_alias="_ArtFachmodell",
    )
    artteilmodell: str = Field(
        validation_alias=AliasChoices("artteilmodell", "_ArtTeilmodell"),
        serialization_alias="_ArtTeilmodell",
    )
    auftraggeber: str = Field(
        validation_alias=AliasChoices("auftraggeber", "_Auftraggeber"),
        serialization_alias="_Auftraggeber",
    )
    ersteller: str = Field(
        validation_alias=AliasChoices("ersteller", "_Ersteller"),
        serialization_alias="_Ersteller",
    )
    erstelldatum: datetime.date = Field(
        validation_alias=AliasChoices("erstelldatum", "_Erstelldatum"),
        serialization_alias="_Erstelldatum",
        default_factory=datetime.date.today,
    )

    gemobjektkatalog: str = Field(
        validation_alias=AliasChoices("gemobjektkatalog", "_GemObjektkatalog"),
        serialization_alias="_GemObjektkatalog",
    )
    projektname: str = Field(
        validation_alias=AliasChoices("projektname", "_Projektname"),
        serialization_alias="_Projektname",
    )
    projektnummer: str = Field(
        validation_alias=AliasChoices("projektnummer", "_Projektnummer"),
        serialization_alias="_Projektnummer",
    )


class Pset_Georeferenzierung(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Georeferenzierung"
    hoehenstatus: str = Field(
        validation_alias=AliasChoices("hoehenstatus", "_Hoehenstatus"),
        serialization_alias="_Hoehenstatus",
    )
    hoehensystem: str = Field(
        validation_alias=AliasChoices("hoehensystem", "_Hoehensystem"),
        serialization_alias="_Hoehensystem",
    )
    koordinatensystem: str = Field(
        validation_alias=AliasChoices("koordinatensystem", "_Koordinatensystem"),
        serialization_alias="_Koordinatensystem",
    )
    lagestatus: str = Field(
        validation_alias=AliasChoices("lagestatus", "_Lagestatus"),
        serialization_alias="_Lagestatus",
    )


class Pset_Hyperlink(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Hyperlink"
    hyperlink_001: Optional[str] = Field(
        default="www.bim.hamburg.de",
        validation_alias=AliasChoices("hyperlink_001", "_Hyperlink_001", "hyperlink1"),
        serialization_alias="_Hyperlink_001",
    )
    hyperlink_001_bemerkung: Optional[str] = Field(
        default="LinkZurHomepageVonBIM.Hamburg",
        validation_alias=AliasChoices("hyperlink_001_bemerkung", "_Hyperlink_001_Bemerkung", "hyperlink1bem"),
        serialization_alias="_Hyperlink_001_Bemerkung",
    )


class Nullpunktobjekt(PropertySetTemplate):
    pset_objektinformation: Optional[Pset_Objektinformation] = None
    pset_modellinformation: Optional[Pset_Modellinformation] = None
    pset_georeferenzierung: Optional[Pset_Georeferenzierung] = None
    pset_hyperlink: Optional[Pset_Hyperlink] = None
