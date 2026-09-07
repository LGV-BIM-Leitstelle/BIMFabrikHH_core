"""City model applications for BIMFabrikHH.

:class:`CityBasicApp` (**deprecated**, use :class:`CityGenericApp` or
:class:`CityRustApp`) writes
LoD1/LoD2 city models via ``ifcopenshell.api`` — the old path that also
handles ``IfcIndexedPolygonalFaceWithVoids`` for LoD2 courtyards.

:class:`CityGenericApp` writes the same geometry via the
``ifcfactory`` ``BIMFactoryElement`` pipeline — shorter code and
batched O(n) container assignment, at the cost of possibly losing
LoD2 void geometry when ``IfcShapeBuilder.mesh`` cannot emit
``IfcIndexedPolygonalFaceWithVoids``.

:class:`CityRustApp` writes CityGML / CityJSON to IFC4 STEP through
``bimfabrikhh_core_rs`` (``mode="mesh"`` or ``mode="typed"``).
"""

from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building, Pset_Objektinformation_CityModel

from .basic.app import CityBasicApp
from .generic.app import CityGenericApp
from .generic_entity import CityGenericEntityApp, parse_typed_gml_files
from .generic_rust import CityRustApp
from .parser import CityGMLParser
from .processing import parse_gml_files

__all__ = [
    "CityBasicApp",
    "CityGenericApp",
    "CityGenericEntityApp",
    "CityRustApp",
    "CityGMLParser",
    "parse_gml_files",
    "parse_typed_gml_files",
    "Building",
    "Pset_Objektinformation_CityModel",
]
