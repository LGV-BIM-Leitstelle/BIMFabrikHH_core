from typing import ClassVar, Optional

from pydantic import BaseModel, Field


class Pset_Objektinformation_Tree(BaseModel):
    pset_name: ClassVar[str] = "Pset_Objektinformation"
    baumnummer: Optional[str] = Field(alias="baumnummer")
    gattung_deutsch: Optional[str] = Field(alias="gattung_deutsch")
    baumid: Optional[int] = Field(alias="baumid")
    art_deutsch: Optional[str] = Field(alias="art_deutsch")
    sorte_deutsch: Optional[str] = Field(alias="sorte_deutsch")
    pflanzjahr: Optional[int] = Field(alias="pflanzjahr")
    kronendurchmesser: Optional[float] = Field(alias="kronendurchmesser")
    stammumfang: Optional[float] = Field(alias="stammumfang")


class Pset_DGM_Tree(BaseModel):
    pset_name: ClassVar[str] = "Pset_DGM"
    strasse: Optional[str] = Field(alias="strasse")
    stadtteil: Optional[str] = Field(alias="stadtteil")
    bezirk: Optional[str] = Field(alias="bezirk")
