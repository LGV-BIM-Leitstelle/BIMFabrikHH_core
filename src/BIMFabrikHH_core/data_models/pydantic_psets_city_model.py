from typing import List, Optional, Tuple

from pydantic import BaseModel, Field

from .city_objektartenkatalog.objektartenkatalog import objektartenkatalog_dachform, objektartenkatalog_hamburg


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
