"""Smoke tests for :class:`TreesRustApp` (needs ``bimfabrikhh_core_rs``)."""

from __future__ import annotations

from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np
import pytest

from BIMFabrikHH_core.apps.trees import build_tree_psets, full_tree_height
from BIMFabrikHH_core.apps.trees.generic.app import TreesGenericApp
from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp, _attributes, _tree_dict
from BIMFabrikHH_core.data_models import TreeRecord

pytest.importorskip("bimfabrikhh_core_rs")


def _record(**overrides) -> TreeRecord:
    data = dict(
        name="Baum_001",
        position=(565100.0, 5933600.0, 5.0),
        kronendurchmesser=5.0,
        stammdurchmesser=0.6,
        detail=1,
        segments=8,
        baumhoehe=4.0,
    )
    data.update(overrides)
    return TreeRecord(**data)


def test_trees_rust_app_empty_records_returns_none() -> None:
    assert TreesRustApp.build_ifc([]) is None


def test_tree_dict_uses_shared_dimensions() -> None:
    d = _tree_dict(_record(), name_prefix="", trunk_color=(112, 69, 46), crown_color=(33, 128, 46))
    assert d["name"] == "Baum_001"
    assert d["trunk_radius"] == pytest.approx(0.3)
    assert d["crown_radius"] == pytest.approx(2.5)
    assert d["is_stump"] is False
    assert d["attributes"]["stammdurchmesser"] == "0.6"


def test_attributes_publish_the_pset_gesamthoehe_not_the_trunk() -> None:
    """``_Baumhoehe`` must be the Gesamthöhe, not ``record.baumhoehe``."""
    stammhoehe, kronendurchmesser = 8.85, 9.56
    gesamthoehe, remark = full_tree_height(stammhoehe, kronendurchmesser)
    record = _record(
        baumhoehe=stammhoehe,
        kronendurchmesser=kronendurchmesser,
        psets=build_tree_psets(
            baumnummer="001",
            gattung="Eiche",
            art="Quercus robur",
            pflanzjahr=1990,
            kronendurchmesser_m=kronendurchmesser,
            stammdurchmesser_m=0.6,
            baumhoehe_m=gesamthoehe,
            baumhoehe_bemerkung=remark,
            aufnahmedatum="2026-09-12",
        ),
    )
    attrs = _attributes(record)
    assert gesamthoehe == pytest.approx(18.41)
    assert attrs["baumhoehe"] == "18.41"


def test_attributes_fall_back_to_the_record_without_psets() -> None:
    attrs = _attributes(_record(baumhoehe=4.0, psets={}))
    assert attrs["baumhoehe"] == "4.0"
    assert attrs["name"] == "Baum_001"


def test_trees_rust_app_writes_ifc(tmp_path: Path) -> None:
    dest = tmp_path / "trees.ifc"
    written = TreesRustApp.build_ifc([_record()], output_path=dest, include_property_sets=True, source_epsg=25832)
    assert written == dest
    text = dest.read_text()
    assert text.startswith("ISO-10303-21")
    assert "IFCBUILDINGELEMENTPROXY" in text
    assert "Baum_001" in text


def _nullpunkt(path: Path):
    model = ifcopenshell.open(str(path))
    (nullpunkt,) = [e for e in model.by_type("IfcBuildingElementProxy") if e.Name == "Nullpunktobjekt"]
    psets = {
        name: {k: v for k, v in props.items() if k != "id"}
        for name, props in ifcopenshell.util.element.get_psets(nullpunkt).items()
    }
    layers = {layer.Name for layer in ifcopenshell.util.element.get_layers(model, nullpunkt)}
    return psets, layers


def test_trees_rust_nullpunkt_matches_generic(tmp_path: Path) -> None:
    basepoint_psets = {
        "Pset_Objektinformation": {
            "_IDEbene1": "Nullpunktobjekt",
            "_IDEbene2": "Nullpunktobjekt",
            "_IDEbene3": "Nullpunktobjekt",
        },
        "Pset_Hyperlink": {"_Hyperlink_001": "https://bim.hamburg.de", "_Hyperlink_001_bemerkung": "Text"},
    }
    common = dict(source_epsg=25832, basepoint_origin=(565000.0, 5933500.0), basepoint_psets=basepoint_psets)
    rust = TreesRustApp.build_ifc([_record()], output_path=tmp_path / "rust.ifc", **common)
    generic = TreesGenericApp.build_ifc([_record()], output_path=tmp_path / "generic.ifc", **common)

    rust_psets, rust_layers = _nullpunkt(rust)
    generic_psets, _ = _nullpunkt(generic)
    assert rust_psets == generic_psets
    assert rust_psets["Pset_Hyperlink"]["_Hyperlink_001_Bemerkung"] == "Text"
    assert "_Projektnullpunkt" in rust_layers


def _nullpunkt_geometry(path: Path):
    model = ifcopenshell.open(str(path))
    (nullpunkt,) = [e for e in model.by_type("IfcBuildingElementProxy") if e.Name == "Nullpunktobjekt"]
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    shape = ifcopenshell.geom.create_shape(settings, nullpunkt)
    vertices = {tuple(v) for v in np.array(shape.geometry.verts).reshape(-1, 3).round(4)}
    items = {
        layer.Name: len([i for i in layer.AssignedItems if i.is_a("IfcRepresentationItem")])
        for layer in model.by_type("IfcPresentationLayerAssignment")
        if layer.Name.startswith("_Projektnullpunkt")
    }
    return vertices, len(shape.geometry.faces) // 3, items


@pytest.mark.parametrize("size", [1.0, 5.0])
def test_trees_rust_nullpunkt_geometry_matches_generic(tmp_path: Path, size: float) -> None:
    common = dict(source_epsg=25832, basepoint_origin=(565000.0, 5933500.0), basepoint_size=size)
    rust = TreesRustApp.build_ifc([_record()], output_path=tmp_path / "rust.ifc", **common)
    generic = TreesGenericApp.build_ifc([_record()], output_path=tmp_path / "generic.ifc", **common)

    rust_vertices, rust_triangles, rust_items = _nullpunkt_geometry(rust)
    generic_vertices, generic_triangles, generic_items = _nullpunkt_geometry(generic)
    assert rust_vertices == generic_vertices
    assert rust_triangles == generic_triangles
    assert rust_items == generic_items == {"_Projektnullpunkt": 1, "_Projektnullpunkt_pfeil": 3}
    assert max(z for _, _, z in rust_vertices) == pytest.approx(size)


def _value_types(path: Path) -> dict:
    model = ifcopenshell.open(str(path))
    return {
        (pset.Name, prop.Name): prop.NominalValue.is_a()
        for pset in model.by_type("IfcPropertySet")
        for prop in pset.HasProperties
        if prop.NominalValue is not None
    }


def test_trees_rust_value_types_match_generic(tmp_path: Path) -> None:
    gesamthoehe, remark = full_tree_height(8.85, 9.56)
    record = _record(
        psets=build_tree_psets(
            baumnummer="001",
            gattung="Eiche",
            art="Quercus robur",
            pflanzjahr=1990,
            kronendurchmesser_m=9.56,
            stammdurchmesser_m=0.6,
            baumhoehe_m=gesamthoehe,
            baumhoehe_bemerkung=remark,
            aufnahmedatum="2026-09-12",
        )
    )
    rust = TreesRustApp.build_ifc([record], output_path=tmp_path / "rust.ifc", source_epsg=25832)
    generic = TreesGenericApp.build_ifc([record], output_path=tmp_path / "generic.ifc", source_epsg=25832)
    rust_types, generic_types = _value_types(rust), _value_types(generic)
    shared = rust_types.keys() & generic_types.keys()
    assert ("Pset_Objektinformation", "_Baumhoehe") in shared
    assert {k: rust_types[k] for k in shared} == {k: generic_types[k] for k in shared}
    assert rust_types[("Pset_Objektinformation", "_Baumnummer")] == "IfcLabel"


def test_trees_rust_nullpunkt_without_psets(tmp_path: Path) -> None:
    written = TreesRustApp.build_ifc(
        [_record()], output_path=tmp_path / "rust.ifc", source_epsg=25832, basepoint_origin=(565000.0, 5933500.0)
    )
    psets, layers = _nullpunkt(written)
    assert psets == {}
    assert "_Projektnullpunkt" in layers
