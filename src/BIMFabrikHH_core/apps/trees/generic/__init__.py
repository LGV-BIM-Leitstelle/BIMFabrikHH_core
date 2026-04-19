"""Generic trees IFC export (Pydantic records + ifcfactory BIMFactoryElement)."""

from BIMFabrikHH_core.data_models import TreeRecord

from .app import TreesGenericApp

__all__ = ["TreesGenericApp", "TreeRecord"]
