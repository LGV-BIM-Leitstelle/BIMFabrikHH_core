"""Tests for the refactored terrain app and its processing helpers.

Covers the pure pieces that don't require a full IFC environment:
:class:`TerrainMesh` semantics, the Pydantic DGM pset defaults, the
Delaunay mesh generator, and the record-builder guard for empty input.
"""

from __future__ import annotations

import numpy as np
import pytest

from BIMFabrikHH_core.apps.terrain import (
    Pset_Objektinformation_DGM,
    TerrainBasicApp,
    TerrainMesh,
    generate_delaunay_mesh,
)
from BIMFabrikHH_core.data_models import RequestParams


# ---------------------------------------------------------------------------
# TerrainMesh
# ---------------------------------------------------------------------------


def test_terrain_mesh_defaults_are_empty() -> None:
    mesh = TerrainMesh()
    assert mesh.vertices == []
    assert mesh.faces == []
    assert mesh.nullpunkt is None
    assert mesh.is_empty() is True


def test_terrain_mesh_is_not_empty_when_geometry_is_set() -> None:
    mesh = TerrainMesh(
        vertices=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        faces=[[0, 1, 2]],
        nullpunkt=(0.0, 0.0),
    )
    assert mesh.is_empty() is False
    assert mesh.nullpunkt == (0.0, 0.0)


def test_terrain_mesh_is_empty_when_only_vertices_exist() -> None:
    mesh = TerrainMesh(vertices=[[0.0, 0.0, 0.0]], faces=[])
    assert mesh.is_empty() is True


# ---------------------------------------------------------------------------
# Pset_Objektinformation_DGM
# ---------------------------------------------------------------------------


def test_pset_objektinformation_dgm_defaults_match_template() -> None:
    """Defaults must mirror the BIM.HH DGM property-set template."""
    data = Pset_Objektinformation_DGM().model_dump(by_alias=True)
    assert data["_ArtDGM"] == "Netz"
    assert data["_AufnahmedatumHinweis"] == "undefiniert"
    assert data["_AufnahmedatumVermessung"] == "undefiniert"
    assert data["_Bauphase"] == "Vorarbeiten"
    assert data["_Bemerkung"] == "undefiniert"
    assert data["_DatenHerkunft"] == "SDP"
    assert data["_IDEbene1"] == "Gelaende"
    assert data["_IDEbene2"] == "Erdoberflaeche"
    assert data["_IDEbene3"] == "Erdoberflaeche"
    assert data["_LoG"] == 300
    assert data["_LoI"] == 100


def test_pset_objektinformation_dgm_accepts_alias_inputs() -> None:
    pset = Pset_Objektinformation_DGM(
        _ArtDGM="TIN",
        _AufnahmedatumVermessung="2025-09-08",
        _LoG=200,
    )
    data = pset.model_dump(by_alias=True)
    assert data["_ArtDGM"] == "TIN"
    assert data["_AufnahmedatumVermessung"] == "2025-09-08"
    assert data["_LoG"] == 200


def test_pset_objektinformation_dgm_pset_name() -> None:
    assert Pset_Objektinformation_DGM.pset_name == "Pset_Objektinformation"


# ---------------------------------------------------------------------------
# generate_delaunay_mesh
# ---------------------------------------------------------------------------


def test_generate_delaunay_mesh_returns_expected_shapes() -> None:
    """A flat 4-corner square must produce 2 triangles over 4 vertices."""
    x = np.array([0.0, 1.0, 1.0, 0.0])
    y = np.array([0.0, 0.0, 1.0, 1.0])
    z = np.array([0.0, 0.0, 0.0, 0.0])

    vertices, faces = generate_delaunay_mesh(x, y, z)

    assert len(vertices) == 4
    assert len(faces) == 2
    for face in faces:
        assert len(face) == 3
        for idx in face:
            assert 0 <= idx < len(vertices)


def test_generate_delaunay_mesh_too_few_points_returns_empty() -> None:
    x = np.array([0.0, 1.0])
    y = np.array([0.0, 0.0])
    z = np.array([0.0, 0.0])

    vertices, faces = generate_delaunay_mesh(x, y, z)

    assert vertices == []
    assert faces == []


# ---------------------------------------------------------------------------
# TerrainBasicApp.build_ifc (empty-input guard)
# ---------------------------------------------------------------------------


def test_build_ifc_returns_none_for_empty_mesh() -> None:
    """``build_ifc`` must short-circuit on an empty mesh without raising."""
    request = RequestParams(bbox=None, containers=[])
    result = TerrainBasicApp.build_ifc(TerrainMesh(), request_params=request)
    assert result is None


@pytest.mark.parametrize(
    "vertices, faces",
    [
        ([], [[0, 1, 2]]),
        ([[0.0, 0.0, 0.0]], []),
    ],
)
def test_build_ifc_returns_none_for_partial_mesh(vertices, faces) -> None:
    request = RequestParams(bbox=None, containers=[])
    mesh = TerrainMesh(vertices=vertices, faces=faces)
    assert TerrainBasicApp.build_ifc(mesh, request_params=request) is None
