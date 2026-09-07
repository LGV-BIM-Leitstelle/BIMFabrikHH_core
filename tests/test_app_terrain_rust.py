"""Smoke tests for :class:`TerrainRustApp` (needs ``bimfabrikhh_core_rs``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from BIMFabrikHH_core.apps.terrain.generic_rust.app import TerrainRustApp
from BIMFabrikHH_core.data_models import RequestParams, TerrainMesh

pytest.importorskip("bimfabrikhh_core_rs")


def _mesh() -> TerrainMesh:
    return TerrainMesh(
        vertices=[
            [565000.0, 5933000.0, 4.0],
            [565010.0, 5933000.0, 4.2],
            [565000.0, 5933010.0, 4.1],
        ],
        faces=[[0, 1, 2]],
        nullpunkt=(565000.0, 5933000.0),
    )


def test_terrain_rust_app_empty_mesh_returns_none() -> None:
    request = RequestParams(bbox=None, containers=[])
    assert TerrainRustApp.build_ifc(TerrainMesh(), request_params=request) is None


def test_terrain_rust_app_writes_ifc(tmp_path: Path) -> None:
    dest = tmp_path / "dgm.ifc"
    written = TerrainRustApp.build_ifc(
        _mesh(),
        request_params=RequestParams(bbox=None, containers=[]),
        output_path=dest,
    )
    assert written == dest
    text = dest.read_text()
    assert text.startswith("ISO-10303-21")
    assert "IFCBUILDINGELEMENTPROXY" in text
    assert "DGM" in text
