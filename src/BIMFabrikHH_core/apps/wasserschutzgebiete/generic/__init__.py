"""Generic Wasserschutzgebiete IFC export (extruded API polygons)."""

from BIMFabrikHH_core.data_models.pydantic_psets_wasserschutzgebiete import Pset_Objektinformation_Wasserschutzgebiet
from BIMFabrikHH_core.data_models.wasserschutzgebiete import (
    GeometryCrs,
    WasserschutzgebietRecord,
    collect_wasserschutz_psets,
    load_wasserschutzgebiete_records,
    records_from_geojson_feature_collection,
)

from .app import WasserschutzgebieteGenericApp

__all__ = [
    "WasserschutzgebieteGenericApp",
    "GeometryCrs",
    "WasserschutzgebietRecord",
    "collect_wasserschutz_psets",
    "load_wasserschutzgebiete_records",
    "records_from_geojson_feature_collection",
    "Pset_Objektinformation_Wasserschutzgebiet",
]
