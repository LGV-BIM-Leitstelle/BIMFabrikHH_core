from unittest.mock import MagicMock, Mock

import pytest

from BIMFabrikHH_core.apps.biotopes.generic import app
from BIMFabrikHH_core.apps.biotopes.generic.app import (
    BiotopesGenericApp,
    _get_line_thickness,
    _line_biotope_element_from_record,
    _point_biotope_element_from_record,
    _polygon_biotope_element_from_record,
)
from BIMFabrikHH_core.core.ogc_extractor.geojson import PolygonRings
from BIMFabrikHH_core.data_models.biotopes import BiotopeRecord, BiotopeShape


@pytest.fixture
def biotope_record():
    return BiotopeRecord(
        feature_id=123,
        shape_type=BiotopeShape.AREA,
        polygons=[PolygonRings(exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], holes=[])],
        lines=None,
        point=None,
        objectid=1,
        id_biotop=1001,
        dk5=1234,
        biotop_nr=5,
        abschnitt=1,
        is_protected=True,
        hauptbiotoptyp="NRT",
        nebenbiotoptypen="",
        naechste_kartierung=None,
    )


@pytest.fixture
def element_options(biotope_record):
    return {
        "record": biotope_record,
        "extrusion_depth": 30.0,
        "color": (100, 150, 200),
        "cad_layer": "_BIM_Biotop",
        "transparency": 0.5,
        "overwrite_hyperlink": None,
        "include_property_sets": True,
    }


def test_polygon_element_creation(element_options):
    result = _polygon_biotope_element_from_record(
        multipolygon=[PolygonRings(exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)], holes=[])],
        **element_options,
    )

    assert result.type == "IfcBuildingElementProxy"
    assert result.name == "Biotop_area_1001"
    assert len(result.children) == 1


def test_polygon_element_with_hole(element_options):
    result = _polygon_biotope_element_from_record(
        multipolygon=[
            PolygonRings(
                exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
                holes=[[(2, 2), (2, 4), (4, 4), (4, 2), (2, 2)]],
            )
        ],
        **element_options,
    )

    assert len(result.children) == 1


def test_line_element_creation(element_options):
    element_options["record"].shape_type = app.BiotopeShape.LINES

    result = _line_biotope_element_from_record(
        lines=[[(0, 0), (10, 10)]],
        **element_options,
    )

    assert result.type == "IfcBuildingElementProxy"
    assert result.name == "Biotop_lines_1001"
    assert len(result.children) == 1


@pytest.mark.parametrize(
    ("width", "expected"),
    [
        (None, 2.0),
        (0.0, 0.0),
        (4.5, 4.5),
        (10.0, 10.0),
    ],
)
def test_line_thickness(width, expected, biotope_record):
    biotope_record.breite_lineares_objekt = width

    assert _get_line_thickness(biotope_record) == expected


def test_point_element_creation(element_options):
    element_options["record"].shape_type = app.BiotopeShape.POINT

    result = _point_biotope_element_from_record(
        point=(100, 200),
        **element_options,
    )

    assert result.type == "IfcBuildingElementProxy"
    assert result.name == "Biotop_point_1001"
    assert len(result.children) == 1


def test_element_creation_without_property_sets(element_options):
    element_options["include_property_sets"] = False

    result = _polygon_biotope_element_from_record(
        multipolygon=[
            PolygonRings(
                exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
                holes=[],
            )
        ],
        **element_options,
    )

    assert result.psets == []


def test_element_creation_with_hyperlink(element_options):
    from BIMFabrikHH_core.data_models.biotopes import build_biotope_hyperlink

    hyperlink = build_biotope_hyperlink(
        "https://example.com/1001",
        1001,
    )

    result = _polygon_biotope_element_from_record(
        multipolygon=[
            PolygonRings(
                exterior=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)],
                holes=[],
            )
        ],
        **{
            **element_options,
            "overwrite_hyperlink": hyperlink,
        },
    )

    assert hyperlink in result.psets
