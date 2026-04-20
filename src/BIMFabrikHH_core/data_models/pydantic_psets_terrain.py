"""Pydantic property set templates for terrain (DGM) IFC exports.

Defaults reflect the current Hamburg BIM-Leitstelle DGM template (``_ArtDGM``
in ``Pset_Objektinformation`` with ``_IDEbene*`` values ``Gelaende`` /
``Erdoberflaeche``). Callers can override any field individually.
"""

from __future__ import annotations

from typing import ClassVar

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, Field


class Pset_Objektinformation_DGM(PropertySetTemplate):
    """``Pset_Objektinformation`` specialized for terrain (DGM) objects."""

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    art_dgm: str = Field(
        validation_alias=AliasChoices("art_dgm", "_ArtDGM"),
        serialization_alias="_ArtDGM",
        default="Netz",
    )
    aufnahmedatum_hinweis: str = Field(
        validation_alias=AliasChoices("aufnahmedatum_hinweis", "_AufnahmedatumHinweis"),
        serialization_alias="_AufnahmedatumHinweis",
        default="undefiniert",
    )
    aufnahmedatum_vermessung: str = Field(
        validation_alias=AliasChoices("aufnahmedatum_vermessung", "_AufnahmedatumVermessung"),
        serialization_alias="_AufnahmedatumVermessung",
        default="undefiniert",
    )
    bauphase: str = Field(
        validation_alias=AliasChoices("bauphase", "_Bauphase"),
        serialization_alias="_Bauphase",
        default="Vorarbeiten",
    )
    bemerkung: str = Field(
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
        default="undefiniert",
    )
    datenherkunft: str = Field(
        validation_alias=AliasChoices("datenherkunft", "_DatenHerkunft"),
        serialization_alias="_DatenHerkunft",
        default="SDP",
    )
    idebene1: str = Field(
        validation_alias=AliasChoices("idebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
        default="Gelaende",
    )
    idebene2: str = Field(
        validation_alias=AliasChoices("idebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
        default="Erdoberflaeche",
    )
    idebene3: str = Field(
        validation_alias=AliasChoices("idebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
        default="Erdoberflaeche",
    )
    log: int = Field(
        validation_alias=AliasChoices("log", "_LoG"),
        serialization_alias="_LoG",
        default=300,
    )
    loi: int = Field(
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
        default=100,
    )
