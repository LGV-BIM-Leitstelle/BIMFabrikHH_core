from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from ifcfactory._internal.pset_base import Length, Quantity
from pydantic import AliasChoices, Field


class Pset_Objektinformation_Tree(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Objektinformation"

    # Tree-specific information
    art_baum: str = Field(
        validation_alias=AliasChoices("art_baum", "_ArtBaum"),
        serialization_alias="_ArtBaum",
        default="undefiniert",
    )
    # art_deutsch: str = Field(
    #     validation_alias=AliasChoices("art_deutsch", "_Art"),
    #     serialization_alias="_Art",
    #     default="undefiniert",
    # )
    aufnahmedatum_vermessung: str = Field(
        validation_alias=AliasChoices("aufnahmedatum_vermessung", "_AufnahmedatumVermessung"),
        serialization_alias="_AufnahmedatumVermessung",
        default="undefiniert",
    )
    # aufnahme_stand: str = Field(
    #     validation_alias=AliasChoices("aufnahme_stand", "_AufnahmeStand"),
    #     serialization_alias="_AufnahmeStand",
    #     default="beschädigt",
    # )
    # baumid: Optional[int] = Field(
    #     validation_alias=AliasChoices("baumid", "_BaumID"),
    #     serialization_alias="_BaumID",
    #     default=None,
    # )
    baumhoehe: Optional[Quantity[Length]] = Field(
        validation_alias=AliasChoices("baumhoehe", "_Baumhoehe"),
        serialization_alias="_Baumhoehe",
        default=None,
    )
    baumhoehe_bemerkung: str = Field(
        validation_alias=AliasChoices("baumhoehe_bemerkung", "_BaumhoeheBemerkung"),
        serialization_alias="_BaumhoeheBemerkung",
        default="undefiniert",
    )
    baumnummer: str = Field(
        validation_alias=AliasChoices("baumnummer", "_Baumnummer"),
        serialization_alias="_Baumnummer",
        default="undefiniert",
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="undefiniert",
    )
    bezirk: str = Field(
        validation_alias=AliasChoices("bezirk", "_Bezirk"),
        serialization_alias="_Bezirk",
        default="undefiniert",
    )
    gattung_deutsch: str = Field(
        validation_alias=AliasChoices("gattung_deutsch", "_Gattung"),
        serialization_alias="_Gattung",
        default="undefiniert",
    )
    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Gehoelz",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Baum",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Baum",
    )
    kronendurchmesser: Quantity[Length] = Field(
        validation_alias=AliasChoices("kronendurchmesser", "_Kronendurchmesser"),
        serialization_alias="_Kronendurchmesser",
        default=None,
    )
    log: int = Field(
        validation_alias=AliasChoices("log", "_LoG"),
        serialization_alias="_LoG",
        default=100,
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=100,
    )
    # mehrstaemmig: bool = Field(
    #     validation_alias=AliasChoices("mehrstaemmig", "_Mehrstaemmig"),
    #     serialization_alias="_Mehrstaemmig",
    #     default=True,
    # )
    pflanzjahr: int = Field(
        validation_alias=AliasChoices("pflanzjahr", "_Pflanzjahr"),
        serialization_alias="_Pflanzjahr",
        default=9999,
    )
    stadtteil: str = Field(
        validation_alias=AliasChoices("stadtteil", "_Stadtteil"),
        serialization_alias="_Stadtteil",
        default="undefiniert",
    )
    stammdurchmesser: Optional[Quantity[Length]] = Field(
        validation_alias=AliasChoices("stammdurchmesser", "_Stammdurchmesser"),
        serialization_alias="_Stammdurchmesser",
        default=None,
    )
    # stammdurchmesser_unten: Optional[Quantity[Length]] = Field(
    #     validation_alias=AliasChoices("stammdurchmesser_unten", "_StammdurchmesserUnten"),
    #     serialization_alias="_StammdurchmesserUnten",
    #     default=None,
    # )
    # stammumfang: Optional[Quantity[Length]] = Field(
    #     validation_alias=AliasChoices("stammumfang", "_Stammumfang"),
    #     serialization_alias="_Stammumfang",
    #     default=None,
    # )
    status_vegetation: str = Field(
        validation_alias=AliasChoices("status_vegetation", "_StatusVegetation"),
        serialization_alias="_StatusVegetation",
        default="undefiniert",
    )
    # sorte_deutsch: Optional[str] = Field(
    #     validation_alias=AliasChoices("sorte_deutsch", "_Sorte"),
    #     serialization_alias="_Sorte",
    #     default="undefiniert",
    # )


class Pset_Bauwerk_Tree(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Bauwerk"

    strassenname: str = Field(
        validation_alias=AliasChoices("strassenname", "_Strassenname"),
        serialization_alias="_Strassenname",
        default="undefiniert",
    )
