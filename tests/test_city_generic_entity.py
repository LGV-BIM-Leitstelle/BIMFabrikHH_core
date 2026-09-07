"""Tests for city generic_entity helpers."""

from BIMFabrikHH_core.apps.city.generic_entity import app as generic_entity_app
from BIMFabrikHH_core.apps.city.generic_entity.models import mapping_registry


def test_mapping_registry_wall_surface() -> None:
    m = mapping_registry()
    assert m["WallSurface"] == "IfcWall"
    assert m["RoofSurface"] == "IfcRoof"


def test_ifc_root_name_from_gml() -> None:
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", None) == "gml-id-1"
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", "  ") == "gml-id-1"
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", "Gebäude A") == "Gebäude A_gml-id-1"
