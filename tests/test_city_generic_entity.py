"""Tests for city generic_entity helpers."""

from BIMFabrikHH_core.apps.city.generic_entity import app as generic_entity_app
from BIMFabrikHH_core.apps.city.generic_entity.mapping import mapping_registry
from BIMFabrikHH_core.apps.city.generic_entity.mesh_utils import ring_to_fan_mesh


def test_ring_to_fan_mesh_triangle() -> None:
    ring = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)]
    v, f = ring_to_fan_mesh(ring)
    assert len(v) == 3
    assert f == [[0, 1, 2]]


def test_ring_to_fan_mesh_quad() -> None:
    ring = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0)]
    _v, f = ring_to_fan_mesh(ring)
    assert len(f) == 2


def test_mapping_registry_wall_surface() -> None:
    m = mapping_registry()
    assert m["WallSurface"] == "IfcWall"
    assert m["RoofSurface"] == "IfcRoof"


def test_ifc_root_name_from_gml() -> None:
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", None) == "gml-id-1"
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", "  ") == "gml-id-1"
    assert generic_entity_app._ifc_root_name_from_gml("gml-id-1", "Gebäude A") == "gml-id-1_Gebäude A"
