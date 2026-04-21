"""City model applications for BIMFabrikHH.

:class:`CityBasicApp` writes LoD1/LoD2 city models via
``ifcopenshell.api`` — the reference path that also handles
``IfcIndexedPolygonalFaceWithVoids`` for LoD2 courtyards faithfully.

:class:`CityGenericApp` writes the same geometry via the
``ifcfactory`` ``BIMFactoryElement`` pipeline — shorter code and
batched O(n) container assignment, at the cost of possibly losing
LoD2 void geometry when ``IfcShapeBuilder.mesh`` cannot emit
``IfcIndexedPolygonalFaceWithVoids``.
"""

from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building, Pset_Objektinformation_CityModel

from .basic.app import CityBasicApp
from .generic.app import CityGenericApp
from .parser import CityGMLParser
from .processing import parse_gml_files

__all__ = [
    "CityBasicApp",
    "CityGenericApp",
    "CityGMLParser",
    "parse_gml_files",
    "Building",
    "Pset_Objektinformation_CityModel",
]
