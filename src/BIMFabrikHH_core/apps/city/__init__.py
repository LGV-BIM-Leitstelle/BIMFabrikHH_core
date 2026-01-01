"""
City Model application for BIMFabrikHH.

This module contains functionality for processing CityGML files and
converting them to IFC building models.
"""

from BIMFabrikHH_core.apps.interface import UIAppInterface
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

# Expose the modular city app following the same interface pattern as other modular apps
from .app import CityModularApp

__all__ = [
    "CityModularApp",
    "PrimitiveCityApp",
    "Building",
    "UIAppInterface",
]
