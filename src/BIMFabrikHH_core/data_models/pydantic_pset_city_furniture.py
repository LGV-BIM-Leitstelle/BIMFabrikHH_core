from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Cityfurniture(PropertySetTemplate):
    """
    Pydantic model for city furniture attributes.
    Based on the Objektinformation structure.
    """

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: Optional[str] = Field(
        default="undefiniert", validation_alias=AliasChoices("idebene1", "IDEbene1"), serialization_alias="_IDEbene1"
    )
    idebene2: Optional[str] = Field(
        default="undefiniert", validation_alias=AliasChoices("idebene2", "IDEbene2"), serialization_alias="_IDEbene2"
    )
    idebene3: Optional[str] = Field(
        default="undefiniert", validation_alias=AliasChoices("idebene3", "IDEbene3"), serialization_alias="_IDEbene3"
    )
    loi: Optional[int] = Field(default=100, serialization_alias="_LoI")
    log: Optional[int] = Field(default=200, serialization_alias="_LoG")
    bemerkung: Optional[str] = Field(default="undefiniert", serialization_alias="_Bemerkung")
