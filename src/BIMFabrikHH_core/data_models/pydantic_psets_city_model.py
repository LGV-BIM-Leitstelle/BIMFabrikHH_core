from typing import ClassVar, List, Optional, Tuple

from ifcfactory import PropertySetTemplate
from pydantic import AliasChoices, BaseModel, Field

from .city_objektartenkatalog.objektartenkatalog import objektartenkatalog_dachform, objektartenkatalog_hamburg


class Pset_Objektinformation_CityModel(PropertySetTemplate):
    """``Pset_Objektinformation`` carrying LoD1/LoD2 city-building attributes.

    Structural twin of :class:`CityModelAttributes`, but built on
    :class:`ifcfactory.PropertySetTemplate` so it can be passed directly
    to ``BIMFactoryElement(psets=[...])`` (used by :class:`CityGenericApp`).

    Use :func:`city_attrs_to_pset` to convert a ``CityModelAttributes``
    instance (which is what :class:`Building` already carries) into this
    pset while applying the ``_FunktionGebaeude`` / ``_Dachform`` label
    maps.
    """

    pset_name: ClassVar[str] = "Pset_Objektinformation"

    id_ebene1: Optional[str] = Field(
        default="Stadtmodell",
        validation_alias=AliasChoices("id_ebene1", "_IDEbene1"),
        serialization_alias="_IDEbene1",
    )
    id_ebene2: Optional[str] = Field(
        default="Stadtmodell",
        validation_alias=AliasChoices("id_ebene2", "_IDEbene2"),
        serialization_alias="_IDEbene2",
    )
    id_ebene3: Optional[str] = Field(
        default="Stadtmodell",
        validation_alias=AliasChoices("id_ebene3", "_IDEbene3"),
        serialization_alias="_IDEbene3",
    )
    loi: Optional[int] = Field(
        default=300,
        validation_alias=AliasChoices("loi", "_LoI"),
        serialization_alias="_LoI",
    )
    bemerkung: Optional[str] = Field(
        default="undefiniert",
        validation_alias=AliasChoices("bemerkung", "_Bemerkung"),
        serialization_alias="_Bemerkung",
    )
    stadtmodell_lod: Optional[str] = Field(
        default="undefiniert",
        validation_alias=AliasChoices("stadtmodell_lod", "_StadtmodellLoD"),
        serialization_alias="_StadtmodellLoD",
    )
    funktion_gebaeude: Optional[str] = Field(
        default="undefiniert",
        validation_alias=AliasChoices("funktion_gebaeude", "_FunktionGebaeude"),
        serialization_alias="_FunktionGebaeude",
    )
    relative_hoehe: Optional[float] = Field(
        default=0.0,
        validation_alias=AliasChoices("relative_hoehe", "_RelativeHoehe"),
        serialization_alias="_RelativeHoehe",
    )
    anzahl_obergeschoss: Optional[int] = Field(
        default=1,
        validation_alias=AliasChoices("anzahl_obergeschoss", "_AnzahlObergeschoss"),
        serialization_alias="_AnzahlObergeschoss",
    )
    dachform: Optional[str] = Field(
        default="undefiniert",
        validation_alias=AliasChoices("dachform", "_Dachform"),
        serialization_alias="_Dachform",
    )


class CityModelAttributes(BaseModel):
    """
    Pydantic model for city model building attributes.
    Based on the Objektinformation structure.
    """

    # Building identification
    id_ebene1: Optional[str] = Field(default="Stadtmodell", serialization_alias="_IDEbene1")
    id_ebene2: Optional[str] = Field(default="Stadtmodell", serialization_alias="_IDEbene2")
    id_ebene3: Optional[str] = Field(default="Stadtmodell", serialization_alias="_IDEbene3")
    loi: Optional[int] = Field(default=300, serialization_alias="_LoI")
    bemerkung: Optional[str] = Field(default="undefiniert", serialization_alias="_Bemerkung")
    stadtmodell_lod: Optional[str] = Field(default="undefiniert", serialization_alias="_StadtmodellLoD")
    funktion_gebaeude: Optional[str] = Field(default="undefiniert", serialization_alias="_FunktionGebaeude")
    relative_hoehe: Optional[float] = Field(default=0.0, serialization_alias="_RelativeHoehe")
    anzahl_obergeschoss: Optional[int] = Field(default=1, serialization_alias="_AnzahlObergeschoss")
    dachform: Optional[str] = Field(default="undefiniert", serialization_alias="_Dachform")

    def to_dict_with_labels(self, function_map=objektartenkatalog_hamburg, by_alias=False) -> dict:
        data = self.model_dump(by_alias=by_alias)
        data["_FunktionGebaeude"] = function_map.get(self.funktion_gebaeude, "undefiniert")
        data["_Dachform"] = objektartenkatalog_dachform.get(self.dachform, "undefiniert")
        return data


class Building(BaseModel):
    id: str
    attributes: CityModelAttributes
    vertices: List[Tuple[float, float, float]]
    faces: List[List[int]]
    faces_with_voids: Optional[List] = Field(
        default=None, description="Faces with void information for IfcIndexedPolygonalFaceWithVoids"
    )


class CityModelBuildingData(BaseModel):
    """Container for city model building data"""

    buildings: List[Building]


def create_city_model_attributes(**kwargs) -> CityModelAttributes:
    """Create city model attributes with default values"""
    return CityModelAttributes(**kwargs)


def get_default_city_model_attributes() -> CityModelAttributes:
    """Get default city model attributes"""
    return CityModelAttributes()


def city_attrs_to_pset(
    attrs: CityModelAttributes,
    function_map=objektartenkatalog_hamburg,
) -> Pset_Objektinformation_CityModel:
    """Convert :class:`CityModelAttributes` to a :class:`PropertySetTemplate`.

    Applies the ``_FunktionGebaeude`` and ``_Dachform`` lookup maps that
    are applied by :meth:`CityModelAttributes.to_dict_with_labels` in
    the basic app, so the generic app produces equivalent property
    values when psets are written by ``BIMFactoryElement``.
    """
    base = attrs.model_dump(by_alias=False)
    base["funktion_gebaeude"] = function_map.get(attrs.funktion_gebaeude, "undefiniert")
    base["dachform"] = objektartenkatalog_dachform.get(attrs.dachform, "undefiniert")
    return Pset_Objektinformation_CityModel(**base)
