"""``Pset_Objektinformation`` template for ALKIS Flurstueck IFC elements.

Mirrors the BIM.Hamburg Merkmalsgruppe *Klasse Flurstueck V002*
(Merkmalsgruppe lists ``IfcSpace``; this app writes ``IfcBuildingElementProxy``).
All eleven Merkmale of that Merkmalsgruppe are present:

* ``_IDEbene1`` / ``_IDEbene2`` / ``_IDEbene3``, ``_LoG``, ``_LoI`` and
  ``_Bemerkung`` are BIM structuring metadata. ``_IDEbene3`` stays
  ``Flurstueck`` and ``_LoI`` is ``300``, matching the delivered PHN
  reference model — they have no counterpart in the API.
* ``_ALKISIdentifikator``, ``_AmtlicheFlaeche``, ``_Flurstueckkennzeichen`` and
  ``_GemarkungName`` come straight from ``alkis_vereinfacht / Flurstueck``.
* ``_LZIbeginnt`` is derived from the API field ``aktualit``, which is
  date-only; see :attr:`BIMFabrikHH_core.data_models.flurstuecke.FlurstueckRecord.element_lzibeginnt`.
"""

from __future__ import annotations

from typing import ClassVar, Literal, Optional

from ifcfactory import PropertySetTemplate
from ifcfactory._internal.pset_base import Quantity
from pydantic import AliasChoices, Field

# ``ifcfactory._internal.pset_base`` only ships ``Length`` / ``Time``; area maps
# to ``IfcAreaMeasure`` via ``pint_to_ifc[Dim("[length]") ** 2]``.
Area = Literal["[length]**2"]


class Pset_Objektinformation_Flurstueck(PropertySetTemplate):
    """Property set for one ALKIS Flurstueck, per Merkmalsgruppe Flurstueck V002."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Flurstueck",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Flurstueck",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Flurstueck",
    )
    log: int = Field(
        validation_alias=AliasChoices("log", "_LoG"),
        serialization_alias="_LoG",
        default=100,
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=300,
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="undefiniert",
    )
    alkisidentifikator: str = Field(
        validation_alias=AliasChoices("alkisidentifikator", "_ALKISIdentifikator"),
        serialization_alias="_ALKISIdentifikator",
        default="",
    )
    amtlicheflaeche: Optional[Quantity[Area]] = Field(
        validation_alias=AliasChoices("amtlicheflaeche", "_AmtlicheFlaeche"),
        serialization_alias="_AmtlicheFlaeche",
        default=None,
    )
    flurstueckkennzeichen: str = Field(
        validation_alias=AliasChoices("flurstueckkennzeichen", "_Flurstueckkennzeichen"),
        serialization_alias="_Flurstueckkennzeichen",
        default="",
    )
    gemarkungname: str = Field(
        validation_alias=AliasChoices("gemarkungname", "_GemarkungName"),
        serialization_alias="_GemarkungName",
        default="",
    )
    lzibeginnt: str = Field(
        validation_alias=AliasChoices("lzibeginnt", "_LZIbeginnt"),
        serialization_alias="_LZIbeginnt",
        default="undefiniert",
    )


__all__ = [
    "Area",
    "Pset_Objektinformation_Flurstueck",
]
