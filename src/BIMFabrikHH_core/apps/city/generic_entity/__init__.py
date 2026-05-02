"""Typed CityGML → IFC export (:mod:`ifcfactory` pipeline)."""

from BIMFabrikHH_core.apps.city.generic_entity.app import CityGenericEntityApp
from BIMFabrikHH_core.apps.city.generic_entity.models import (
    BoundarySurfaceMapping,
    BoundaryPolygon,
    DEFAULT_BOUNDARY_MAPPINGS,
    mapping_registry,
)
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import TypedCityBuilding
from BIMFabrikHH_core.apps.city.generic_entity.parser import (
    CityGMLTypedSurfaceParser,
    extract_building_typed,
    parse_typed_gml_files,
)
from BIMFabrikHH_core.apps.city.generic_entity.quantities import (
    FaceQuantities,
    Pset_BIMFabrikHH_Quantities,
    compute_boundary_quantities,
    face_quantities_to_pset,
    polygon_gross_area,
    polygon_perimeter,
    polygon_slope_deg,
)

__all__ = [
    "BoundaryPolygon",
    "BoundarySurfaceMapping",
    "CityGenericEntityApp",
    "CityGMLTypedSurfaceParser",
    "DEFAULT_BOUNDARY_MAPPINGS",
    "FaceQuantities",
    "Pset_BIMFabrikHH_Quantities",
    "TypedCityBuilding",
    "compute_boundary_quantities",
    "extract_building_typed",
    "face_quantities_to_pset",
    "mapping_registry",
    "parse_typed_gml_files",
    "polygon_gross_area",
    "polygon_perimeter",
    "polygon_slope_deg",
]
