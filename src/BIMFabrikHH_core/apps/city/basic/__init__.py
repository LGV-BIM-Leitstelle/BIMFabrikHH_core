"""Deprecated. Use :class:`CityGenericApp` or :class:`CityRustApp`.

Basic city-model IFC export via ``ifcopenshell.api``.
"""

from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

from .app import CityBasicApp

__all__ = ["CityBasicApp", "Building"]
