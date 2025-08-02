from typing import ClassVar, Optional

from pydantic import Field

from .pset_base import Quantity, Length, PropertySetTemplate


class Pset_Objektinformation_Tree(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Objektinformation"
    baumnummer: Optional[str] = Field(alias="baumnummer", default=None)
    gattung_deutsch: Optional[str] = Field(alias="gattung_deutsch", default=None)
    baumid: Optional[int] = Field(alias="baumid", default=None)
    art_deutsch: Optional[str] = Field(alias="art_deutsch", default=None)
    sorte_deutsch: Optional[str] = Field(alias="sorte_deutsch", default=None)
    pflanzjahr: Optional[int] = Field(alias="pflanzjahr", default=None)
    kronendurchmesser: Optional[Quantity[Length]] = Field(alias="kronendurchmesser", default=None)
    stammumfang: Optional[Quantity[Length]] = Field(alias="stammumfang", default=None)


class Pset_DGM_Tree(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_DGM"
    strasse: Optional[str] = Field(alias="strasse")
    stadtteil: Optional[str] = Field(alias="stadtteil")
    bezirk: Optional[str] = Field(alias="bezirk")
