from typing import ClassVar, Optional

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Pset_Hyperlink(PropertySetTemplate):
    pset_name: ClassVar[str] = "Pset_Hyperlink"
    hyperlink_001: Optional[str] = Field(
        default="www.bim.hamburg.de",
        validation_alias=AliasChoices("hyperlink_001", "_Hyperlink_001", "hyperlink1"),
        serialization_alias="_Hyperlink_001",
    )
    hyperlink_001_bemerkung: Optional[str] = Field(
        default="Link_zur_Homepage_von_BIM.Hamburg",
        validation_alias=AliasChoices("hyperlink_001_bemerkung", "_Hyperlink_001_Bemerkung", "hyperlink1bem"),
        serialization_alias="_Hyperlink_001_Bemerkung",
    )
