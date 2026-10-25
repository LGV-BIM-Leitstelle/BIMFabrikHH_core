"""Source / output EPSG: no EPSG means no CRS, ``source_epsg`` declares it, ``output_epsg`` transforms."""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Iterable, Optional, Tuple

import ifcopenshell
import numpy as np
import pytest
from ifcopenshell.util.placement import get_local_placement
from pyproj import Transformer

from BIMFabrikHH_core.apps.boreholes.generic.app import BoreholesGenericApp
from BIMFabrikHH_core.apps.city.processing import citygml_crs, with_tile_crs
from BIMFabrikHH_core.apps.flurstuecke.generic.app import FlurstueckeGenericApp
from BIMFabrikHH_core.apps.streets.processing import dgm_output_transformer, transformer_to_dgm
from BIMFabrikHH_core.apps.terrain.processing import resolve_guide_records, transform_mesh
from BIMFabrikHH_core.apps.trees import check_positions_in_dgm_crs, transform_record_positions
from BIMFabrikHH_core.apps.trees.generic.app import TreesGenericApp
from BIMFabrikHH_core.apps.wasserschutzgebiete.generic.app import WasserschutzgebieteGenericApp
from BIMFabrikHH_core.core.geometry import basepoint_xy
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer, warn_if_degree_coordinates
from BIMFabrikHH_core.core.model_creator import georeference_options
from BIMFabrikHH_core.core.ogc_extractor import PolygonRings
from BIMFabrikHH_core.data_models import TreeRecord, check_projected_epsg, check_source_epsg, check_vertical_epsg
from BIMFabrikHH_core.data_models.boreholes import BoreholeLayer, BoreholeRecord
from BIMFabrikHH_core.data_models.flurstuecke import FlurstueckRecord
from BIMFabrikHH_core.data_models.params_tree import BoundingBoxParams, RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystem, CoordinateSystemTemplates
from BIMFabrikHH_core.data_models.streets import StreetRecord
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh
from BIMFabrikHH_core.data_models.wasserschutzgebiete import WasserschutzgebietRecord

HAMBURG_BBOX = BoundingBoxParams(min_x=9.98, min_y=53.54, max_x=10.00, max_y=53.56)
HAMBURG_BBOX_TUPLE = (9.98, 53.54, 10.00, 53.56)
POINT_25832 = (565100.0, 5933600.0)
GK = 10285


def _to_gk(x: float, y: float) -> Tuple[float, float]:
    return Transformer.from_crs(25832, GK, always_xy=True).transform(x, y)


def _request(source_epsg: Optional[int] = None, output_epsg: Optional[int] = None) -> RequestParams:
    return RequestParams(bbox=HAMBURG_BBOX, source_epsg=source_epsg, output_epsg=output_epsg)


def _xy_points(path: Path) -> Iterable[Tuple[float, float]]:
    model = ifcopenshell.open(str(path))
    for point in model.by_type("IfcCartesianPoint"):
        if len(point.Coordinates) >= 2:
            yield point.Coordinates[0], point.Coordinates[1]
    for plist in model.by_type("IfcCartesianPointList3D"):
        for coord in plist.CoordList:
            yield coord[0], coord[1]


def _nearest(path: Path, xy: Tuple[float, float]) -> float:
    return min(math.dist(p, xy) for p in _xy_points(path))


def _crs_name(path: Path) -> Optional[str]:
    crs = ifcopenshell.open(str(path)).by_type("IfcProjectedCRS")
    return crs[0].Name if crs else None


def _has_georeferencing(path: Path) -> bool:
    model = ifcopenshell.open(str(path))
    return bool(model.by_type("IfcProjectedCRS") or model.by_type("IfcMapConversion"))


def _has_basepoint(path: Path) -> bool:
    return any(p.Name and "Nullpunkt" in p.Name for p in ifcopenshell.open(str(path)).by_type("IfcBuildingElementProxy"))


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------


def test_coordinate_system_from_epsg_fills_header_fields() -> None:
    cs = CoordinateSystem.from_epsg(GK)
    assert cs.name == "EPSG:10285"
    assert cs.geodetic_datum == "ETRS89/DREF91/2016"
    assert cs.vertical_datum is None
    assert cs.map_zone == "3"
    assert CoordinateSystem.from_epsg(GK, vertical_epsg=7837).vertical_datum == "EPSG:7837"


def test_coordinate_system_from_epsg_matches_25832_template() -> None:
    template = CoordinateSystemTemplates.epsg_25832()
    assert CoordinateSystem.from_epsg(25832) == template.model_copy(update={"vertical_datum": None})


@pytest.mark.parametrize("epsg", [25832, GK, 31467])
def test_check_projected_epsg_accepts_projected_metre_crs(epsg: int) -> None:
    check_projected_epsg(epsg, HAMBURG_BBOX_TUPLE)


@pytest.mark.parametrize(
    "epsg",
    [
        4326,  # geographic
        5555,  # compound (25832 + DHHN2016)
        2263,  # US feet
        999999,  # unknown
    ],
)
def test_check_projected_epsg_rejects(epsg: int) -> None:
    with pytest.raises(ValueError):
        check_projected_epsg(epsg)


def test_check_projected_epsg_rejects_bbox_outside_area_of_use() -> None:
    """UTM zone 33 covers 12°E-18°E; Hamburg lies at 10°E."""
    with pytest.raises(ValueError, match="area of use"):
        check_projected_epsg(25833, HAMBURG_BBOX_TUPLE)


@pytest.mark.parametrize(
    ("source", "output"),
    [
        (25832, None),
        (GK, None),
        (4326, 25832),  # WGS84 longitude / latitude
        (4979, 25832),  # WGS84 3D
        (5555, GK),  # compound: 25832 + DHHN92 height
    ],
)
def test_check_source_epsg_accepts(source: int, output: Optional[int]) -> None:
    check_source_epsg(source, output, HAMBURG_BBOX_TUPLE)


@pytest.mark.parametrize(
    "source",
    [
        4978,  # geocentric
        7837,  # DHHN2016 height only
        999999,  # unknown
    ],
)
def test_check_source_epsg_rejects_without_horizontal_crs(source: int) -> None:
    with pytest.raises(ValueError):
        check_source_epsg(source, 25832)


@pytest.mark.parametrize("source", [4326, 5555])
def test_check_source_epsg_needs_output_when_not_projected_2d(source: int) -> None:
    with pytest.raises(ValueError, match="set output_epsg"):
        check_source_epsg(source)


def test_request_params_epsg_codes_default_to_none() -> None:
    request = _request()
    assert request.source_epsg is None
    assert request.output_epsg is None


def test_request_params_accepts_valid_epsg_codes() -> None:
    request = _request(source_epsg=25832, output_epsg=GK)
    assert (request.source_epsg, request.output_epsg) == (25832, GK)


@pytest.mark.parametrize("field", ["source_epsg", "output_epsg"])
@pytest.mark.parametrize("epsg", [4326, 2263])
def test_request_params_rejects_invalid_epsg_codes(field: str, epsg: int) -> None:
    with pytest.raises(ValueError):
        RequestParams(bbox=HAMBURG_BBOX, **{field: epsg})


def test_request_params_accepts_output_without_source() -> None:
    assert _request(output_epsg=GK).source_epsg is None


def test_request_params_accepts_wgs84_source_with_output() -> None:
    request = _request(source_epsg=4326, output_epsg=25832)
    assert (request.source_epsg, request.output_epsg) == (4326, 25832)


def test_transformer_without_any_epsg_is_none() -> None:
    assert CoordinateTransformer.from_source_to_output(None, None) is None


def test_transformer_output_without_source_raises() -> None:
    with pytest.raises(ValueError, match="source_epsg"):
        CoordinateTransformer.from_source_to_output(None, GK)


def test_transformer_source_only_keeps_source() -> None:
    transformer = CoordinateTransformer.from_source_to_output(GK, None)
    assert transformer.is_identity
    assert transformer.target_epsg == GK


def test_transformer_source_to_output() -> None:
    assert CoordinateTransformer.from_source_to_output(25832, 25832).is_identity
    transformer = CoordinateTransformer.from_source_to_output(25832, GK)
    assert not transformer.is_identity
    assert transformer.target_epsg == GK
    ((x, y),) = transformer.transform_ring([POINT_25832])
    assert (x, y) == pytest.approx(_to_gk(*POINT_25832), abs=1e-6)


def test_transformer_reuses_pyproj_transformer_per_crs_pair() -> None:
    first = CoordinateTransformer.from_source_to_output(25832, GK)
    second = CoordinateTransformer.from_source_to_output(25832, GK)
    assert first.transformer is second.transformer
    assert CoordinateTransformer.from_source_to_output(4326, GK).transformer is not first.transformer


def test_transformer_wgs84_source_to_output() -> None:
    lon, lat = Transformer.from_crs(25832, 4326, always_xy=True).transform(*POINT_25832)
    x, y, _ = CoordinateTransformer.from_source_to_output(4326, 25832).transform_point(lon, lat)
    assert (x, y) == pytest.approx(POINT_25832, abs=1e-3)


def test_transformer_compound_source_uses_horizontal_part() -> None:
    compound = CoordinateTransformer.from_source_to_output(5555, GK).transform_point(*POINT_25832)
    assert compound[:2] == pytest.approx(_to_gk(*POINT_25832), abs=1e-6)


@pytest.mark.parametrize(
    ("source", "vertical", "expected"),
    [
        (25832, None, None),  # 2D source, no height system given
        (25832, 7837, "EPSG:7837"),  # DHHN2016
        (5555, None, "EPSG:5783"),  # compound source names DHHN92
        (5555, 5783, "EPSG:5783"),
    ],
)
def test_georeference_options_vertical_datum(source: int, vertical: Optional[int], expected: Optional[str]) -> None:
    transformer = CoordinateTransformer.from_source_to_output(source, GK, vertical)
    coordinate_system = georeference_options(transformer)["coordinate_system"]
    assert (coordinate_system.name, coordinate_system.vertical_datum) == ("EPSG:10285", expected)


def test_georeference_options_without_transformer_writes_no_crs() -> None:
    assert georeference_options(None) == {"georeferenced": False}


@pytest.mark.parametrize(
    ("source", "vertical"),
    [
        (25832, 25832),  # horizontal, not vertical
        (25832, 5555),  # compound, not vertical
        (5555, 7837),  # contradicts the DHHN92 of 5555
    ],
)
def test_vertical_epsg_rejected(source: int, vertical: int) -> None:
    with pytest.raises(ValueError):
        check_vertical_epsg(vertical, source)
    with pytest.raises(ValueError):
        CoordinateTransformer.from_source_to_output(source, GK, vertical)


def test_vertical_epsg_without_source_raises() -> None:
    with pytest.raises(ValueError, match="needs source_epsg"):
        CoordinateTransformer.from_source_to_output(None, None, 7837)


def test_request_params_vertical_epsg() -> None:
    assert RequestParams(bbox=HAMBURG_BBOX, vertical_epsg=7837).vertical_epsg == 7837
    with pytest.raises(ValueError):
        RequestParams(bbox=HAMBURG_BBOX, source_epsg=5555, output_epsg=GK, vertical_epsg=7837)


@pytest.mark.parametrize(("source", "output"), [(4326, None), (25832, 4326), (4978, 25832)])
def test_transformer_rejects_invalid_pairs(source: int, output: Optional[int]) -> None:
    with pytest.raises(ValueError):
        CoordinateTransformer.from_source_to_output(source, output)


def test_warn_if_degree_coordinates(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_degree_coordinates([(9.98, 53.55)], None)
        warn_if_degree_coordinates(iter([(9.98, 53.55, 0.0)]), CoordinateTransformer.from_source_to_output(25832, None))
    assert len([r for r in caplog.records if "longitude / latitude" in r.getMessage()]) == 2


def test_warn_if_degree_coordinates_stays_quiet(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        warn_if_degree_coordinates([], None)
        warn_if_degree_coordinates([(9.98, 53.55), POINT_25832], None)
        warn_if_degree_coordinates([(9.98, 53.55)], CoordinateTransformer.from_source_to_output(4326, 25832))
    assert not [r for r in caplog.records if "longitude / latitude" in r.getMessage()]


def test_basepoint_xy_transforms_explicit_origin() -> None:
    transformer = CoordinateTransformer.from_source_to_output(25832, GK)
    xy = basepoint_xy(basepoint_origin=POINT_25832, bbox_wgs84=None, transformer=transformer)
    assert xy == pytest.approx(_to_gk(*POINT_25832), abs=1e-6)


def test_basepoint_xy_bbox_lower_left_in_output_crs() -> None:
    transformer = CoordinateTransformer.from_source_to_output(25832, GK)
    xy = basepoint_xy(basepoint_origin=None, bbox_wgs84=HAMBURG_BBOX_TUPLE, transformer=transformer)
    ll = Transformer.from_crs(4326, GK, always_xy=True).transform(9.98, 53.54)
    assert xy is not None
    assert xy[0] == pytest.approx(ll[0], abs=200)
    assert xy[1] == pytest.approx(ll[1], abs=200)


def test_transform_record_positions_keeps_height() -> None:
    record = TreeRecord(name="T", position=(*POINT_25832, 7.5), kronendurchmesser=5.0, stammdurchmesser=0.3)
    (moved,) = transform_record_positions([record], CoordinateTransformer.from_source_to_output(25832, GK))
    assert moved.position[:2] == pytest.approx(_to_gk(*POINT_25832), abs=1e-6)
    assert moved.position[2] == 7.5
    assert record.position[0] == POINT_25832[0]


def test_transform_record_positions_without_transformer_keeps_positions() -> None:
    record = TreeRecord(name="T", position=(*POINT_25832, 7.5), kronendurchmesser=5.0, stammdurchmesser=0.3)
    assert transform_record_positions([record], None)[0].position == record.position


# ---------------------------------------------------------------------------
# Trees
# ---------------------------------------------------------------------------


def _tree(xy: Tuple[float, float] = POINT_25832) -> TreeRecord:
    return TreeRecord(
        name="Baum_A",
        position=(*xy, 5.0),
        kronendurchmesser=5.0,
        stammdurchmesser=0.4,
        detail=1,
        segments=8,
        baumhoehe=10.0,
    )


def test_trees_generic_without_epsg_has_no_crs(tmp_path: Path) -> None:
    path = TreesGenericApp.build_ifc([_tree()], output_path=tmp_path / "trees.ifc", bbox_wgs84=HAMBURG_BBOX_TUPLE)
    assert not _has_georeferencing(path)
    assert not _has_basepoint(path)
    assert _nearest(path, POINT_25832) < 5.0


def test_trees_generic_without_epsg_keeps_explicit_basepoint(tmp_path: Path) -> None:
    path = TreesGenericApp.build_ifc([_tree()], output_path=tmp_path / "trees.ifc", basepoint_origin=POINT_25832)
    assert not _has_georeferencing(path)
    assert _has_basepoint(path)


def test_trees_generic_source_epsg_alone_is_not_transformed(tmp_path: Path) -> None:
    gk_xy = _to_gk(*POINT_25832)
    path = TreesGenericApp.build_ifc([_tree(gk_xy)], output_path=tmp_path / "trees.ifc", source_epsg=GK)
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, gk_xy) < 5.0


def test_trees_generic_transforms_source_to_output(tmp_path: Path) -> None:
    path = TreesGenericApp.build_ifc(
        [_tree()],
        output_path=tmp_path / "trees.ifc",
        source_epsg=25832,
        output_epsg=GK,
        basepoint_origin=POINT_25832,
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 5.0
    assert _nearest(path, POINT_25832) > 1000.0


def test_trees_generic_transforms_wgs84_source(tmp_path: Path) -> None:
    lonlat = Transformer.from_crs(25832, 4326, always_xy=True).transform(*POINT_25832)
    path = TreesGenericApp.build_ifc(
        [_tree(lonlat)], output_path=tmp_path / "trees.ifc", source_epsg=4326, output_epsg=25832
    )
    assert _crs_name(path) == "EPSG:25832"
    assert _nearest(path, POINT_25832) < 5.0


def test_trees_generic_wgs84_source_without_output_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="set output_epsg"):
        TreesGenericApp.build_ifc([_tree((9.98, 53.55))], output_path=tmp_path / "trees.ifc", source_epsg=4326)


def test_trees_generic_warns_for_degree_positions_without_epsg(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING):
        TreesGenericApp.build_ifc([_tree((9.98, 53.55))], output_path=tmp_path / "trees.ifc")
    assert any("longitude / latitude" in r.getMessage() for r in caplog.records)


def test_trees_generic_output_without_source_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_epsg"):
        TreesGenericApp.build_ifc([_tree()], output_path=tmp_path / "trees.ifc", output_epsg=GK)


def test_trees_generic_rejects_dgm_with_foreign_source_crs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="DGM draping"):
        TreesGenericApp.build_ifc([_tree()], output_path=tmp_path / "trees.ifc", tif_files=[], source_epsg=GK)


@pytest.mark.parametrize("source", [None, 25832, 5555])
def test_check_positions_in_dgm_crs_accepts_horizontal_tile_crs(source: Optional[int]) -> None:
    output = GK if source == 5555 else None
    check_positions_in_dgm_crs(CoordinateTransformer.from_source_to_output(source, output))


def _crs_header(path: Path) -> Tuple[Optional[str], ...]:
    (crs,) = ifcopenshell.open(str(path)).by_type("IfcProjectedCRS")
    return (crs.Name, crs.Description, crs.GeodeticDatum, crs.VerticalDatum, crs.MapProjection, crs.MapZone)


def test_trees_rust_transforms_source_to_output(tmp_path: Path) -> None:
    pytest.importorskip("bimfabrikhh_core_rs")
    from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp

    path = TreesRustApp.build_ifc([_tree()], output_path=tmp_path / "trees.ifc", source_epsg=25832, output_epsg=GK)
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 5.0


def test_trees_rust_writes_same_crs_header_as_generic(tmp_path: Path) -> None:
    pytest.importorskip("bimfabrikhh_core_rs")
    from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp

    epsg = {"source_epsg": 25832, "output_epsg": GK, "vertical_epsg": 7837}
    rust = TreesRustApp.build_ifc([_tree()], output_path=tmp_path / "rust.ifc", **epsg)
    generic = TreesGenericApp.build_ifc([_tree()], output_path=tmp_path / "generic.ifc", **epsg)
    assert _crs_header(rust) == _crs_header(generic)
    assert _crs_header(rust)[:4] == ("EPSG:10285", CoordinateSystem.from_epsg(GK).description, "ETRS89/DREF91/2016", "EPSG:7837")


def test_trees_rust_without_source_writes_no_georeferencing(tmp_path: Path) -> None:
    pytest.importorskip("bimfabrikhh_core_rs")
    from BIMFabrikHH_core.apps.trees.generic_rust.app import TreesRustApp

    path = TreesRustApp.build_ifc(
        [_tree()], output_path=tmp_path / "trees.ifc", bbox_wgs84=HAMBURG_BBOX_TUPLE
    )
    assert not _has_georeferencing(path)
    assert not _has_basepoint(path)
    assert _nearest(path, POINT_25832) < 5.0


# ---------------------------------------------------------------------------
# Flurstücke / Wasserschutzgebiete / streets / terrain rings
# ---------------------------------------------------------------------------


def _square(x: float, y: float, size: float = 20.0):
    return [(x, y), (x + size, y), (x + size, y + size), (x, y + size), (x, y)]


def _flurstueck(exterior=None) -> FlurstueckRecord:
    return FlurstueckRecord(
        feature_id=1,
        polygons=[PolygonRings(exterior=exterior or _square(*POINT_25832), holes=[])],
        idflurst="DEHHALKA1",
    )


def test_flurstuecke_without_epsg_has_no_crs(tmp_path: Path) -> None:
    path = FlurstueckeGenericApp.build_ifc([_flurstueck()], request_params=_request(), output_path=tmp_path / "f.ifc")
    assert not _has_georeferencing(path)
    assert not _has_basepoint(path)
    assert _nearest(path, POINT_25832) < 0.01


def test_flurstuecke_source_epsg_alone_is_not_transformed(tmp_path: Path) -> None:
    path = FlurstueckeGenericApp.build_ifc(
        [_flurstueck()], request_params=_request(source_epsg=25832), output_path=tmp_path / "f.ifc"
    )
    assert _crs_name(path) == "EPSG:25832"
    assert _nearest(path, POINT_25832) < 0.01


def test_flurstuecke_transforms_source_to_output(tmp_path: Path) -> None:
    path = FlurstueckeGenericApp.build_ifc(
        [_flurstueck()], request_params=_request(source_epsg=25832, output_epsg=GK), output_path=tmp_path / "f.ifc"
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 0.01


def test_flurstuecke_transforms_wgs84_source(tmp_path: Path) -> None:
    to_wgs84 = Transformer.from_crs(25832, 4326, always_xy=True)
    exterior = [to_wgs84.transform(x, y) for x, y in _square(*POINT_25832)]
    path = FlurstueckeGenericApp.build_ifc(
        [_flurstueck(exterior)],
        request_params=_request(source_epsg=4326, output_epsg=GK),
        output_path=tmp_path / "f.ifc",
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 0.01


def test_wasserschutzgebiete_writes_output_epsg(tmp_path: Path) -> None:
    record = WasserschutzgebietRecord(
        feature_id=1,
        exterior_ring=_square(*POINT_25832),
        wsg="WSG",
        gebietsname="Test",
    )
    path = WasserschutzgebieteGenericApp.build_ifc(
        [record], request_params=_request(source_epsg=25832, output_epsg=GK), output_path=tmp_path / "wsg.ifc"
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 0.01


def _street(rings) -> StreetRecord:
    return StreetRecord(feature_id=1, rings=rings, nutzart="Weg")


def test_streets_drape_in_dgm_crs_then_write_output_epsg(tmp_path: Path) -> None:
    from BIMFabrikHH_core.apps.streets.generic.app import StreetsGenericApp

    request = RequestParams(bbox=HAMBURG_BBOX, source_epsg=25832, output_epsg=GK)
    path = StreetsGenericApp.build_ifc(
        [_street([_square(*POINT_25832)])], request_params=request, output_path=tmp_path / "streets.ifc"
    )
    assert _crs_header(path)[::3] == ("EPSG:10285", "EPSG:7837")
    corner = _world_points(path).min(axis=0)
    assert math.dist(corner[:2], _to_gk(*POINT_25832)) < 0.5


def test_resolve_guide_records_transforms_source_into_dgm_crs() -> None:
    to_wgs84 = Transformer.from_crs(25832, 4326, always_xy=True)
    ring = [to_wgs84.transform(x, y) for x, y in _square(*POINT_25832)]
    (record,) = resolve_guide_records([_street([ring])], None, guide_from_oaf=False, source_epsg=4326)
    assert record.rings[0][0] == pytest.approx(POINT_25832, abs=1e-3)


def test_resolve_guide_records_without_source_keeps_rings() -> None:
    ring = _square(*POINT_25832)
    (record,) = resolve_guide_records([_street([ring])], None, guide_from_oaf=False)
    assert record.rings[0] == ring


def test_transformer_to_dgm_without_source_is_none() -> None:
    assert transformer_to_dgm(None) is None
    assert transformer_to_dgm(25832).is_identity


# ---------------------------------------------------------------------------
# Boreholes: source CRS comes from the request
# ---------------------------------------------------------------------------


def _borehole(xy: Tuple[float, float] = POINT_25832) -> BoreholeRecord:
    return BoreholeRecord(
        borehole_id="BDHH_TEST1",
        archive_id="",
        easting=xy[0],
        northing=xy[1],
        ansatzhoehe_nn=14.3,
        groundwater=None,
        layers=[
            BoreholeLayer(
                layer_id="BDHH_TEST1_0",
                from_depth=0.0,
                to_depth=2.3,
                upper_height=14.3,
                lower_height=12.0,
                thickness=2.3,
                hauptgemengteil="mS",
            )
        ],
    )


def test_boreholes_without_epsg_has_no_crs(tmp_path: Path) -> None:
    path = BoreholesGenericApp.build_ifc([_borehole()], request_params=_request(), output_path=tmp_path / "bh.ifc")
    assert not _has_georeferencing(path)
    assert not _has_basepoint(path)
    assert _nearest(path, POINT_25832) < 0.01


def test_boreholes_source_epsg_alone_is_not_transformed(tmp_path: Path) -> None:
    gk_xy = _to_gk(*POINT_25832)
    path = BoreholesGenericApp.build_ifc(
        [_borehole(gk_xy)], request_params=_request(source_epsg=GK), output_path=tmp_path / "bh.ifc"
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _has_basepoint(path)
    assert _nearest(path, gk_xy) < 0.01


def test_boreholes_transforms_source_to_output(tmp_path: Path) -> None:
    path = BoreholesGenericApp.build_ifc(
        [_borehole()], request_params=_request(source_epsg=25832, output_epsg=GK), output_path=tmp_path / "bh.ifc"
    )
    assert _crs_name(path) == "EPSG:10285"
    assert _nearest(path, _to_gk(*POINT_25832)) < 0.01


@pytest.mark.parametrize(
    ("app", "make_record"),
    [
        (BoreholesGenericApp, lambda: _borehole()),
        (FlurstueckeGenericApp, lambda: _flurstueck()),
        (
            WasserschutzgebieteGenericApp,
            lambda: WasserschutzgebietRecord(
                feature_id=1, exterior_ring=_square(*POINT_25832), wsg="WSG", gebietsname="Test"
            ),
        ),
    ],
)
def test_request_apps_output_without_source_raise(app, make_record, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_epsg"):
        app.build_ifc([make_record()], request_params=_request(output_epsg=GK), output_path=tmp_path / "x.ifc")


# ---------------------------------------------------------------------------
# City: generic and Rust share the EPSG handling
# ---------------------------------------------------------------------------

CITY_TILE = Path(__file__).resolve().parents[1] / "examples" / "assets" / "LoD1_32_564_5934_1_HH.xml"
CITY_BUILDING = "DEHHALKAJ0000p7f"


def _city_app(name: str):
    if name == "rust":
        pytest.importorskip("bimfabrikhh_core_rs")
        from BIMFabrikHH_core.apps.city.generic_rust.app import CityRustApp

        return CityRustApp
    from BIMFabrikHH_core.apps.city.generic.app import CityGenericApp

    return CityGenericApp


def _world_points(path: Path) -> np.ndarray:
    """Mesh vertices of all non-basepoint proxies in world coordinates."""
    points = []
    for element in ifcopenshell.open(str(path)).by_type("IfcBuildingElementProxy"):
        if element.Name == "Nullpunktobjekt" or not element.Representation:
            continue
        matrix = get_local_placement(element.ObjectPlacement)
        for representation in element.Representation.Representations:
            for item in representation.Items:
                coords = np.array(item.Coordinates.CoordList)
                points.append((matrix @ np.c_[coords, np.ones(len(coords))].T).T[:, :3])
    return np.vstack(points)


def _city_ifc(
    app_name: str,
    path: Path,
    request: RequestParams,
    building: Optional[str] = CITY_BUILDING,
    tile: Path = CITY_TILE,
) -> Path:
    return _city_app(app_name).from_gml_files(
        [str(tile)], request_params=request, building_id_filter=building, output_path=path
    )


def _tile_without_srs_name(tmp_path: Path) -> Path:
    tile = tmp_path / "no_srs.xml"
    tile.write_text(re.sub(r' srsName="[^"]+"', "", CITY_TILE.read_text(encoding="utf-8")), encoding="utf-8")
    return tile


@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_city_transforms_source_to_output(app_name: str, tmp_path: Path) -> None:
    utm = _city_ifc(app_name, tmp_path / "utm.ifc", RequestParams(source_epsg=25832, vertical_epsg=7837))
    gk = _city_ifc(
        app_name, tmp_path / "gk.ifc", RequestParams(source_epsg=25832, output_epsg=GK, vertical_epsg=7837)
    )
    utm_points, gk_points = _world_points(utm), _world_points(gk)
    expected_x, expected_y = Transformer.from_crs(25832, GK, always_xy=True).transform(
        utm_points[:, 0], utm_points[:, 1]
    )
    assert np.allclose(gk_points[:, 0], expected_x, atol=1e-3)
    assert np.allclose(gk_points[:, 1], expected_y, atol=1e-3)
    assert np.array_equal(gk_points[:, 2], utm_points[:, 2])
    assert _crs_header(gk)[:4] == ("EPSG:10285", CoordinateSystem.from_epsg(GK).description, "ETRS89/DREF91/2016", "EPSG:7837")


def test_city_generic_and_rust_write_the_same_points(tmp_path: Path) -> None:
    bbox = BoundingBoxParams(min_x=9.9647, min_y=53.5531, max_x=9.9711, max_y=53.5564)
    request = RequestParams(bbox=bbox, source_epsg=25832, output_epsg=GK, vertical_epsg=7837)
    generic = _city_ifc("generic", tmp_path / "generic.ifc", request, building=None)
    rust = _city_ifc("rust", tmp_path / "rust.ifc", request, building=None)
    generic_points, rust_points = (np.unique(_world_points(path).round(3), axis=0) for path in (generic, rust))
    assert np.array_equal(generic_points, rust_points)
    assert _crs_header(generic) == _crs_header(rust)


@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_city_without_any_crs_writes_no_georeferencing(app_name: str, tmp_path: Path) -> None:
    path = _city_ifc(app_name, tmp_path / "city.ifc", RequestParams(), tile=_tile_without_srs_name(tmp_path))
    assert not _has_georeferencing(path)
    assert _world_points(path)[:, 0].min() > 500_000


@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_city_bbox_needs_a_crs(app_name: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="source_epsg"):
        _city_ifc(
            app_name, tmp_path / "city.ifc", RequestParams(bbox=HAMBURG_BBOX), tile=_tile_without_srs_name(tmp_path)
        )


@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_city_takes_source_and_vertical_from_tile_srs_name(app_name: str, tmp_path: Path) -> None:
    path = _city_ifc(app_name, tmp_path / "city.ifc", RequestParams(output_epsg=GK))
    assert _crs_header(path)[::3] == ("EPSG:10285", "EPSG:7837")


@pytest.mark.parametrize(
    "request_params",
    [
        RequestParams(source_epsg=25833),  # tile is UTM 32N
        RequestParams(source_epsg=25832, vertical_epsg=5783),  # tile heights are DHHN2016
        RequestParams(source_epsg=5555, output_epsg=25832),  # compound: DHHN92 heights
    ],
)
@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_city_rejects_request_contradicting_tile_srs_name(
    app_name: str, request_params: RequestParams, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="contradicts the city tiles"):
        _city_ifc(app_name, tmp_path / "city.ifc", request_params)


@pytest.mark.parametrize(
    "srs_name, expected",
    [
        ("urn:adv:crs:ETRS89_UTM32*DE_DHHN2016_NH", (25832, 7837)),
        ("urn:adv:crs:ETRS89_UTM33*DE_DHHN92_NH", (25833, 5783)),
        ("urn:adv:crs:ETRS89_UTM32", (25832, None)),
        ("urn:ogc:def:crs,crs:EPSG:6.12:25833,crs:EPSG:6.12:7837", (25833, 7837)),
        ("urn:ogc:def:crs:EPSG::5555", (25832, 5783)),
        ("EPSG:25832", (25832, None)),
        ("http://www.opengis.net/def/crs/EPSG/0/25832", (25832, None)),
        ("EPSG:999999", (None, None)),
        ("local", (None, None)),
    ],
)
def test_citygml_crs(tmp_path: Path, srs_name: str, expected: Tuple[Optional[int], Optional[int]]) -> None:
    tile = tmp_path / "tile.gml"
    tile.write_text(f'<core:CityModel><gml:Envelope srsName="{srs_name}"/></core:CityModel>', encoding="utf-8")
    assert citygml_crs(tile) == expected


def test_citygml_crs_without_srs_name(tmp_path: Path) -> None:
    tile = tmp_path / "tile.gml"
    tile.write_text("<core:CityModel/>", encoding="utf-8")
    assert citygml_crs(tile) == (None, None)
    assert citygml_crs("https://example.org/tile.gml") == (None, None)


def test_with_tile_crs_rejects_tiles_with_different_crs(tmp_path: Path) -> None:
    utm33 = tmp_path / "utm33.xml"
    utm33.write_text(CITY_TILE.read_text(encoding="utf-8").replace("ETRS89_UTM32", "ETRS89_UTM33"), encoding="utf-8")
    with pytest.raises(ValueError, match="different CRS"):
        with_tile_crs(RequestParams(), [CITY_TILE, utm33])


# ---------------------------------------------------------------------------
# Terrain: the DGM mesh is transformed after meshing
# ---------------------------------------------------------------------------


def _dgm_mesh() -> TerrainMesh:
    return TerrainMesh(
        vertices=[[565000.0, 5933000.0, 5.0], [565010.0, 5933000.0, 6.0], [565000.0, 5933010.0, 7.0]],
        faces=[[0, 1, 2]],
        nullpunkt=(565000.0, 5933000.0),
    )


def test_transform_mesh_moves_xy_and_nullpunkt_keeps_z_and_faces() -> None:
    mesh = _dgm_mesh()
    moved = transform_mesh(mesh, dgm_output_transformer(GK))
    assert [v[2] for v in moved.vertices] == [5.0, 6.0, 7.0]
    assert moved.faces == mesh.faces
    for (x, y, _), (gx, gy, _) in zip(mesh.vertices, moved.vertices):
        assert math.dist(_to_gk(x, y), (gx, gy)) < 1e-6
    assert math.dist(_to_gk(*mesh.nullpunkt), moved.nullpunkt) < 1e-6
    assert transform_mesh(mesh, dgm_output_transformer(None)) is mesh


def test_dgm_output_transformer_rejects_move_to_origin_with_output() -> None:
    assert dgm_output_transformer(None, move_to_origin=True).is_identity
    with pytest.raises(ValueError, match="move_to_origin"):
        dgm_output_transformer(GK, move_to_origin=True)


@pytest.mark.parametrize("app_name", ["generic", "rust"])
def test_terrain_from_geotiffs_writes_output_epsg(app_name: str, tmp_path: Path, monkeypatch) -> None:
    if app_name == "rust":
        pytest.importorskip("bimfabrikhh_core_rs")
        from BIMFabrikHH_core.apps.terrain.generic_rust import app as module

        app = module.TerrainRustApp
    else:
        from BIMFabrikHH_core.apps.terrain.generic import app as module

        app = module.TerrainGenericApp
    monkeypatch.setattr(module, "extract_mesh_adaptive", lambda *args, **kwargs: _dgm_mesh())

    path = app.from_geotiffs(
        [], request_params=RequestParams(bbox=HAMBURG_BBOX, output_epsg=GK), output_path=tmp_path / "dgm.ifc"
    )
    assert _crs_header(path)[::3] == ("EPSG:10285", "EPSG:7837")
    assert np.allclose(_world_points(path).min(axis=0)[:2], _to_gk(565000.0, 5933000.0), atol=1e-3)
