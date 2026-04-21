"""Unit tests for the record-builder :class:`CityBasicApp`."""

import inspect
from typing import get_type_hints

import pytest

from BIMFabrikHH_core.apps.city import CityBasicApp, parse_gml_files
from BIMFabrikHH_core.apps.city.processing import _building_overlaps_bbox, _resolve_file_path
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building, CityModelAttributes


class TestCityBasicAppContract:
    """Verify the record-builder contract of :class:`CityBasicApp`."""

    def test_build_ifc_is_staticmethod(self):
        """``build_ifc`` must be callable directly on the class."""
        assert callable(CityBasicApp.build_ifc)

    def test_build_ifc_signature_required_args(self):
        """``build_ifc`` accepts ``buildings`` positional + keyword-only extras."""
        sig = inspect.signature(CityBasicApp.build_ifc)
        params = sig.parameters

        assert "buildings" in params
        assert "request_params" in params
        assert "basepoint_origin" in params
        assert "output_path" in params
        assert "output_name" in params

    def test_from_gml_files_is_classmethod(self):
        """``from_gml_files`` must be callable directly on the class."""
        assert callable(CityBasicApp.from_gml_files)

    def test_from_gml_files_signature(self):
        sig = inspect.signature(CityBasicApp.from_gml_files)
        params = sig.parameters
        for name in ("gml_files", "request_params", "building_id_filter", "basepoint_origin"):
            assert name in params, f"Missing parameter: {name}"

    def test_basepoint_origin_is_optional_tuple(self):
        """The explicit-origin override defaults to ``None``."""
        sig = inspect.signature(CityBasicApp.build_ifc)
        assert sig.parameters["basepoint_origin"].default is None


class TestCityProcessing:
    """Unit tests for the pure data-processing helpers."""

    def test_resolve_file_path_none_folder(self):
        assert _resolve_file_path("tile.xml", None) == "tile.xml"

    def test_resolve_file_path_http_folder(self):
        assert _resolve_file_path("tile.xml", "https://example.com/tiles") == ("https://example.com/tiles/tile.xml")

    def test_resolve_file_path_absolute_folder(self):
        assert _resolve_file_path("tile.xml", "/mnt/assets") == "/mnt/assets/tile.xml"

    def test_resolve_file_path_absolute_file_overrides_mounted(self):
        assert _resolve_file_path("/abs/tile.xml", "/mnt/assets") == "/abs/tile.xml"

    def test_building_overlaps_bbox_inside(self):
        building = _make_building(
            vertices=[(10.0, 10.0, 0.0), (20.0, 10.0, 0.0), (15.0, 20.0, 0.0)],
            faces=[[0, 1, 2]],
        )
        assert _building_overlaps_bbox(building, bbox_epsg=(0.0, 0.0, 100.0, 100.0))

    def test_building_overlaps_bbox_outside(self):
        building = _make_building(
            vertices=[(500.0, 500.0, 0.0), (600.0, 500.0, 0.0), (550.0, 600.0, 0.0)],
            faces=[[0, 1, 2]],
        )
        assert not _building_overlaps_bbox(building, bbox_epsg=(0.0, 0.0, 100.0, 100.0))

    def test_parse_gml_files_with_empty_list(self):
        """``parse_gml_files`` short-circuits cleanly when given nothing."""
        buildings = parse_gml_files([])
        assert buildings == []


class TestCityBasicAppExecution:
    """Smoke test — calling with no buildings must fail gracefully."""

    def test_build_ifc_returns_none_for_empty_input(self):
        request_params = _make_request_params(with_bbox=True)
        result = CityBasicApp.build_ifc(buildings=[], request_params=request_params)
        assert result is None


def _make_building(vertices, faces) -> Building:
    return Building(
        id="test_building",
        attributes=CityModelAttributes(),
        vertices=vertices,
        faces=faces,
    )


def _make_request_params(with_bbox: bool) -> RequestParams:
    bbox = BoundingBoxParams(min_x=9.75, min_y=53.58, max_x=9.76, max_y=53.59) if with_bbox else None
    container = Container(
        containerTitle="Test_Container",
        containerId="test_id",
        components={
            "description": Component(title="Description", value="Test City Model"),
        },
    )
    return RequestParams(bbox=bbox, containers=[container])
