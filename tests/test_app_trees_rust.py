"""Smoke tests for :class:`TreesRustApp` (needs ``bimfabrikhh_core_rs``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp, _tree_dict
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


def test_trees_rust_app_writes_ifc(tmp_path: Path) -> None:
    dest = tmp_path / "trees.ifc"
    written = TreesRustApp.build_ifc([_record()], output_path=dest, include_property_sets=True)
    assert written == dest
    text = dest.read_text()
    assert text.startswith("ISO-10303-21")
    assert "IFCBUILDINGELEMENTPROXY" in text
    assert "Baum_001" in text
