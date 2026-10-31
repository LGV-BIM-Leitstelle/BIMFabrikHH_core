"""A Nullpunkt entered by the user: ``RequestParams.basepoint`` in the CRS of the IFC wins as given."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import ifcopenshell
import pytest
from ifcopenshell.util.placement import get_local_placement
from pydantic import ValidationError

from BIMFabrikHH_core.apps.flurstuecke.generic.app import FlurstueckeGenericApp
from BIMFabrikHH_core.apps.terrain.generic_rust.app import TerrainRustApp
from BIMFabrikHH_core.apps.trees.generic.app import TreesGenericApp
from BIMFabrikHH_core.core.geometry import basepoint_xyz
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer
from BIMFabrikHH_core.core.ogc_extractor import PolygonRings
from BIMFabrikHH_core.data_models import BasepointParams, TreeRecord
from BIMFabrikHH_core.data_models.flurstuecke import FlurstueckRecord
from BIMFabrikHH_core.data_models.params_tree import BoundingBoxParams, RequestParams

HAMBURG_BBOX = BoundingBoxParams(min_x=9.98, min_y=53.54, max_x=10.00, max_y=53.56)
POINT_25832 = (565100.0, 5933600.0)
USER_25832 = (565012.25, 5933559.5, 12.35)
USER_GK = (3565126.05, 5935974.38, 7.5)
GK = 10285


def _nullpunkt_xyz(path: Path) -> Tuple[float, float, float]:
    model = ifcopenshell.open(str(path))
    (proxy,) = [p for p in model.by_type("IfcBuildingElementProxy") if p.Name == "Nullpunktobjekt"]
    x, y, z = get_local_placement(proxy.ObjectPlacement)[:3, 3]
    return float(x), float(y), float(z)


def _tree() -> TreeRecord:
    return TreeRecord(
        name="Baum_A",
        position=(*POINT_25832, 5.0),
        kronendurchmesser=5.0,
        stammdurchmesser=0.4,
        detail=1,
        segments=8,
        baumhoehe=10.0,
    )


def _flurstueck() -> FlurstueckRecord:
    x, y = POINT_25832
    ring = [(x, y), (x + 20, y), (x + 20, y + 20), (x, y + 20), (x, y)]
    return FlurstueckRecord(feature_id=1, polygons=[PolygonRings(exterior=ring, holes=[])], idflurst="DEHHALKA1")


# ---------------------------------------------------------------------------
# RequestParams
# ---------------------------------------------------------------------------


def test_basepoint_height_defaults_to_zero() -> None:
    params = RequestParams(source_epsg=25832, basepoint={"x": USER_25832[0], "y": USER_25832[1]})
    assert params.basepoint_xyz == (USER_25832[0], USER_25832[1], 0.0)


def test_basepoint_is_optional() -> None:
    assert RequestParams(source_epsg=25832).basepoint_xyz is None


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_basepoint_rejects_non_finite_values(value: float) -> None:
    with pytest.raises(ValidationError):
        BasepointParams(x=value, y=5933559.0)


@pytest.mark.parametrize(
    "xy",
    [
        (9.99, 53.55),  # degrees instead of metres
        (5933559.0, 565012.0),  # x / y swapped
    ],
)
def test_basepoint_outside_the_ifc_crs_is_rejected(xy: Tuple[float, float]) -> None:
    with pytest.raises(ValidationError, match="area of use of EPSG:25832"):
        RequestParams(source_epsg=25832, basepoint={"x": xy[0], "y": xy[1]})


def test_basepoint_is_checked_in_the_output_crs() -> None:
    RequestParams(source_epsg=25832, output_epsg=GK, basepoint={"x": USER_GK[0], "y": USER_GK[1]})
    with pytest.raises(ValidationError, match="EPSG:10285"):
        RequestParams(source_epsg=25832, output_epsg=GK, basepoint={"x": POINT_25832[0], "y": POINT_25832[1]})


def test_basepoint_without_any_crs_is_taken_as_given() -> None:
    assert RequestParams(basepoint={"x": 1.0, "y": 2.0, "z": 3.0}).basepoint_xyz == (1.0, 2.0, 3.0)


# ---------------------------------------------------------------------------
# basepoint_xyz
# ---------------------------------------------------------------------------


def test_basepoint_wins_over_origin_and_bbox() -> None:
    transformer = CoordinateTransformer.from_source_to_output(25832, GK)
    xyz = basepoint_xyz(
        basepoint=USER_GK,
        basepoint_origin=POINT_25832,
        bbox_wgs84=(9.98, 53.54, 10.00, 53.56),
        transformer=transformer,
    )
    assert xyz == USER_GK


def test_without_basepoint_the_fallback_is_at_height_zero() -> None:
    xyz = basepoint_xyz(
        basepoint_origin=POINT_25832, transformer=CoordinateTransformer.from_source_to_output(25832, None)
    )
    assert xyz == (*POINT_25832, 0.0)


# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------


def test_flurstuecke_places_the_nullpunkt_at_the_entered_point(tmp_path: Path) -> None:
    params = RequestParams(
        bbox=HAMBURG_BBOX,
        source_epsg=25832,
        output_epsg=GK,
        basepoint={"x": USER_GK[0], "y": USER_GK[1], "z": USER_GK[2]},
    )
    path = FlurstueckeGenericApp.build_ifc([_flurstueck()], request_params=params, output_path=tmp_path / "f.ifc")
    assert _nullpunkt_xyz(path) == pytest.approx(USER_GK)


def test_trees_generic_places_the_nullpunkt_at_the_entered_point(tmp_path: Path) -> None:
    path = TreesGenericApp.build_ifc(
        [_tree()],
        output_path=tmp_path / "trees.ifc",
        source_epsg=25832,
        bbox_wgs84=(9.98, 53.54, 10.00, 53.56),
        basepoint=USER_25832,
    )
    assert _nullpunkt_xyz(path) == pytest.approx(USER_25832)


def test_trees_rust_places_the_nullpunkt_at_the_entered_point(tmp_path: Path) -> None:
    pytest.importorskip("bimfabrikhh_core_rs")
    from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp

    path = TreesRustApp.build_ifc(
        [_tree()],
        output_path=tmp_path / "trees.ifc",
        source_epsg=25832,
        bbox_wgs84=(9.98, 53.54, 10.00, 53.56),
        basepoint=USER_25832,
    )
    assert _nullpunkt_xyz(path) == pytest.approx(USER_25832)


def test_city_rust_passes_the_entered_point(tmp_path: Path) -> None:
    pytest.importorskip("bimfabrikhh_core_rs")
    from BIMFabrikHH_core.apps.city.generic_rust.app import _export_kwargs

    params = RequestParams(
        bbox=HAMBURG_BBOX,
        source_epsg=25832,
        basepoint={"x": USER_25832[0], "y": USER_25832[1], "z": USER_25832[2]},
    )
    kwargs = _export_kwargs(
        params,
        mode="mesh",
        color=None,
        cad_layer=True,
        basepoint_origin=POINT_25832,
        basepoint_size=8.0,
        psets=[],
        ifc_types=None,
        progress=False,
    )
    assert kwargs["basepoint"] == USER_25832


def test_terrain_rust_uses_the_entered_point_and_else_height_zero() -> None:
    params = RequestParams(
        bbox=HAMBURG_BBOX,
        source_epsg=25832,
        basepoint={"x": USER_25832[0], "y": USER_25832[1], "z": USER_25832[2]},
    )
    assert TerrainRustApp._basepoint(POINT_25832, params, None) == USER_25832
    without = RequestParams(bbox=HAMBURG_BBOX, source_epsg=25832)
    assert TerrainRustApp._basepoint(POINT_25832, without, None) == (*POINT_25832, 0.0)
