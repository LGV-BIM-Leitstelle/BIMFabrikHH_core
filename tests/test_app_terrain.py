"""Tests for the refactored terrain app and its processing helpers.

Covers the pure pieces that don't require a full IFC environment:
:class:`TerrainMesh` semantics, the Pydantic DGM pset defaults, the
Delaunay mesh generator, and the record-builder guard for empty input.
"""

from pathlib import Path

import numpy as np
import pytest

import ifcopenshell

from xml.etree import ElementTree as ET

from BIMFabrikHH_core.apps.terrain import (
    GuideRing,
    Pset_Objektinformation_DGM,
    TerrainBasicApp,
    TerrainMesh,
    collect_guide_rings,
    generate_delaunay_mesh,
    split_mesh_by_nutzart,
    terrain_mesh_to_landxml,
)
from BIMFabrikHH_core.apps.terrain.processing import (
    _invalid_z,
    build_water_polygon_meshes,
    drop_points_inside_rings,
    drop_sliver_faces,
    flatten_planar_water_z,
)
from BIMFabrikHH_core.data_models.streets import (
    ALKIS_NUTZUNG_WEITERE_GEOJSON,
    DEFAULT_NUTZARTEN,
    WEITERE_NUTZARTEN,
    StreetRecord,
    write_nutzung_geojson,
)
from BIMFabrikHH_core.data_models import RequestParams
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams

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


def test_drop_sliver_faces_removes_collinear_frame_triangle() -> None:
    vertices = [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [2.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
    faces = [[0, 1, 2], [0, 1, 3]]
    verts, tris = drop_sliver_faces(vertices, faces)
    assert len(tris) == 1
    assert all(len(face) == 3 for face in tris)
    assert len(verts) == 3


def test_invalid_z_treats_zero_fill_and_gdal_nodata() -> None:
    z = np.array([5.0, 0.0, -3.4e38, np.nan, 1.2])
    bad = _invalid_z(z, nodata=-3.4e38)
    assert list(bad) == [False, True, True, True, False]


def test_collect_guide_rings_clips_to_bbox() -> None:
    """Street outlines that leave the crop must be clipped so the TIN stays rectangular."""
    rec = StreetRecord(
        feature_id=1,
        rings=[[(-10.0, -10.0), (20.0, -10.0), (20.0, 20.0), (-10.0, 20.0)]],
        geometry_crs="EPSG:25832",
        nutzart="Strassenverkehr",
    )
    bbox = (0.0, 0.0, 10.0, 10.0)
    rings = collect_guide_rings([rec], spacing=100.0, bbox_utm=bbox)
    assert len(rings) == 1
    xs, ys = rings[0].xy[:, 0], rings[0].xy[:, 1]
    assert rings[0].nutzart == "Strassenverkehr"
    assert xs.min() >= 0.0 - 1e-9
    assert ys.min() >= 0.0 - 1e-9
    assert xs.max() <= 10.0 + 1e-9
    assert ys.max() <= 10.0 + 1e-9


def test_collect_guide_rings_drops_rings_outside_bbox() -> None:
    rec = StreetRecord(
        feature_id=2,
        rings=[[(100.0, 100.0), (110.0, 100.0), (110.0, 110.0)]],
        geometry_crs="EPSG:25832",
    )
    assert collect_guide_rings([rec], spacing=100.0, bbox_utm=(0.0, 0.0, 10.0, 10.0)) == []


def test_split_mesh_by_nutzart_keeps_unknown_types() -> None:
    mesh = TerrainMesh(
        vertices=[[0.0, 0.0, 0.0], [2.0, 0.0, 0.0], [1.0, 2.0, 0.0], [10.0, 10.0, 0.0], [12.0, 10.0, 0.0], [11.0, 12.0, 0.0]],
        faces=[[0, 1, 2], [3, 4, 5]],
    )
    park = GuideRing(
        xy=np.array([[-0.1, -0.1], [2.1, -0.1], [2.1, 2.1], [-0.1, 2.1]]),
        nutzart="Sport Freizeit Und Erholungsflaeche",
        label="Sport Freizeit Und Erholungsflaeche",
    )
    parts = split_mesh_by_nutzart(mesh, [park])
    assert "Sport Freizeit Und Erholungsflaeche" in parts
    assert len(parts["Sport Freizeit Und Erholungsflaeche"].faces) == 1


def test_split_mesh_by_nutzart_groups_one_type() -> None:
    """Two street triangles become one Strassenverkehr mesh; the rest stays DGM."""
    mesh = TerrainMesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [2.0, 2.0, 0.0],
            [0.0, 2.0, 0.0],
            [10.0, 10.0, 0.0],
            [12.0, 10.0, 0.0],
            [10.0, 12.0, 0.0],
        ],
        faces=[[0, 1, 2], [0, 2, 3], [4, 5, 6]],
    )
    street = GuideRing(
        xy=np.array([[-0.1, -0.1], [2.1, -0.1], [2.1, 2.1], [-0.1, 2.1]]),
        nutzart="Strassenverkehr",
    )
    parts = split_mesh_by_nutzart(mesh, [street])
    assert set(parts) == {"DGM", "Strassenverkehr"}
    assert len(parts["Strassenverkehr"].faces) == 2
    assert len(parts["DGM"].faces) == 1


def test_split_mesh_does_not_bridge_separate_same_type_rings() -> None:
    """A CDT face that jumps the gap between two Wohnbau rings stays on DGM."""
    mesh = TerrainMesh(
        vertices=[
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [3.0, 0.0, 0.0],
            [4.0, 0.0, 0.0],
            [3.0, 1.0, 0.0],
        ],
        faces=[
            [0, 1, 2],  # inside left ring
            [3, 4, 5],  # inside right ring
            [1, 3, 2],  # bridge: verts on both rings, centroid in the gap / left
        ],
    )
    left = GuideRing(
        xy=np.array([[-0.1, -0.1], [1.1, -0.1], [1.1, 1.1], [-0.1, 1.1]]),
        nutzart="Wohnbauflaeche",
        label="Wohnbauflaeche",
    )
    right = GuideRing(
        xy=np.array([[2.9, -0.1], [4.1, -0.1], [4.1, 1.1], [2.9, 1.1]]),
        nutzart="Wohnbauflaeche",
        label="Wohnbauflaeche",
    )
    parts = split_mesh_by_nutzart(mesh, [left, right])
    assert len(parts["Wohnbauflaeche"].faces) == 2
    assert len(parts["DGM"].faces) == 1


def test_drop_points_inside_water_rings() -> None:
    ring = GuideRing(
        xy=np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]),
        nutzart="Fliessgewaesser",
    )
    x = np.array([1.0, 3.0])
    y = np.array([1.0, 3.0])
    z = np.array([5.0, 6.0])
    xo, yo, zo = drop_points_inside_rings(x, y, z, [ring])
    assert list(xo) == [3.0]
    assert list(zo) == [6.0]


def test_write_nutzung_geojson_filters_weitere(tmp_path: Path) -> None:
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"nutzart": "Strassenverkehr"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]},
            },
            {
                "type": "Feature",
                "properties": {"nutzart": "Wohnbauflaeche"},
                "geometry": {"type": "Polygon", "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 2]]]},
            },
        ],
    }
    dest = tmp_path / ALKIS_NUTZUNG_WEITERE_GEOJSON
    write_nutzung_geojson(data, dest, nutzarten=WEITERE_NUTZARTEN)
    written = dest.read_text(encoding="utf-8")
    assert "Wohnbauflaeche" in written
    assert "Strassenverkehr" not in written
    assert DEFAULT_NUTZARTEN.isdisjoint(WEITERE_NUTZARTEN)


def test_terrain_mesh_to_landxml_round_trip(tmp_path: Path) -> None:
    ns = {"lx": "http://www.landxml.org/schema/LandXML-1.2"}
    dgm = TerrainMesh(
        vertices=[[10.0, 20.0, 5.0], [12.0, 20.0, 5.5], [11.0, 22.0, 6.0]],
        faces=[[0, 1, 2]],
    )
    # A 4-vertex face must fan-triangulate to 2 <F> entries.
    water = TerrainMesh(
        vertices=[[0.0, 0.0, 1.0], [2.0, 0.0, 1.0], [2.0, 2.0, 1.0], [0.0, 2.0, 1.0]],
        faces=[[0, 1, 2], [0, 2, 3]],
    )
    dest = tmp_path / "dgm.xml"
    terrain_mesh_to_landxml([("DGM", dgm), ("Fliessgewaesser", water)], dest, epsg=25832)

    root = ET.parse(dest).getroot()
    surfaces = root.findall(".//lx:Surface", ns)
    assert [s.get("name") for s in surfaces] == ["DGM", "Fliessgewaesser"]

    cs = root.find(".//lx:CoordinateSystem", ns)
    assert cs is not None and cs.get("epsgCode") == "25832"

    dgm_surface = surfaces[0]
    points = dgm_surface.findall(".//lx:P", ns)
    faces = dgm_surface.findall(".//lx:F", ns)
    assert [p.get("id") for p in points] == ["1", "2", "3"]
    # Point ids are 1-based; face references them.
    assert faces[0].text.split() == ["1", "2", "3"]
    # LandXML order is northing easting elevation (Y X Z).
    assert points[0].text.split() == ["20.0000", "10.0000", "5.0000"]

    water_faces = surfaces[1].findall(".//lx:F", ns)
    assert len(water_faces) == 2


def test_build_water_meshes_are_triangles() -> None:
    ring = GuideRing(
        xy=np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]),
        nutzart="Fliessgewaesser",
    )
    meshes = build_water_polygon_meshes([ring], [np.array([1.0, 1.1, 1.2, 1.0])])
    water = meshes["Fliessgewaesser"]
    # A 4-vertex ring fan-triangulates to 2 triangles, no interior points added.
    assert len(water.vertices) == 4
    assert all(len(face) == 3 for face in water.faces)
    assert len(water.faces) == 2


def test_flatten_planar_water_uses_median() -> None:
    ring = GuideRing(
        xy=np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]),
        nutzart="Stehendes Gewaesser",
    )
    z = np.array([2.0, 4.0, np.nan])
    flatten_planar_water_z([ring], [z])
    assert np.allclose(z, 3.0)


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


def test_build_ifc_omits_nullpunkt_without_bbox_or_explicit_origin(tmp_path: Path) -> None:
    """No basepoint when neither ``basepoint_origin`` nor ``RequestParams.bbox`` is set."""
    mesh = TerrainMesh(
        vertices=[
            [3560000.0, 5930000.0, 0.0],
            [3560100.0, 5930000.0, 0.0],
            [3560000.0, 5930100.0, 0.0],
        ],
        faces=[[0, 1, 2]],
        nullpunkt=(3560000.0, 5930000.0),
    )
    request = RequestParams(bbox=None, containers=[])
    result = TerrainBasicApp.build_ifc(mesh, request_params=request, output_path=tmp_path / "no_bp.ifc")
    assert result is not None
    ifc = ifcopenshell.open(str(result))
    names = [e.Name for e in ifc.by_type("IfcBuildingElementProxy")]
    assert not any(n == "Nullpunktobjekt" for n in names)


def test_build_ifc_places_nullpunkt_from_request_bbox(tmp_path: Path) -> None:
    mesh = TerrainMesh(
        vertices=[
            [3560000.0, 5930000.0, 0.0],
            [3560100.0, 5930000.0, 0.0],
            [3560000.0, 5930100.0, 0.0],
        ],
        faces=[[0, 1, 2]],
        nullpunkt=(3560000.0, 5930000.0),
    )
    request = RequestParams(bbox=BoundingBoxParams(), containers=[])
    result = TerrainBasicApp.build_ifc(mesh, request_params=request, output_path=tmp_path / "with_bp.ifc")
    assert result is not None
    ifc = ifcopenshell.open(str(result))
    names = [e.Name for e in ifc.by_type("IfcBuildingElementProxy")]
    assert "Nullpunktobjekt" in names
