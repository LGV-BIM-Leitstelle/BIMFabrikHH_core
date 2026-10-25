import pytest

from BIMFabrikHH_core.core.ogc_extractor import (
    ensure_feature_collection,
    feature_identifier,
    parse_feature_for_all_polygon_rings,
    parse_feature_polygon_exterior_rings,
    positions_to_xy_ring,
    transform_polygon_rings,
)


def _ring(x0, y0, x1, y1):
    return [
        [x0, y0],
        [x1, y0],
        [x1, y1],
        [x0, y1],
        [x0, y0],
    ]


def _feature(geometry_type, coordinates, feature_id=1):
    return {
        "type": "Feature",
        "id": feature_id,
        "properties": {},
        "geometry": {
            "type": geometry_type,
            "coordinates": coordinates,
        },
    }


@pytest.mark.unit
def test_polygon_preserves_exterior_and_hole():
    exterior = _ring(0, 0, 10, 10)
    hole = _ring(2, 2, 4, 4)

    result = parse_feature_for_all_polygon_rings(_feature("Polygon", [exterior, hole]))

    assert len(result) == 1
    assert result[0].exterior == [(float(x), float(y)) for x, y in exterior]
    assert result[0].holes == [[(float(x), float(y)) for x, y in hole]]


@pytest.mark.unit
def test_polygon_preserves_multiple_holes():
    exterior = _ring(0, 0, 20, 20)
    holes = [
        _ring(2, 2, 4, 4),
        _ring(10, 10, 15, 15),
    ]

    result = parse_feature_for_all_polygon_rings(_feature("Polygon", [exterior, *holes]))

    assert len(result) == 1
    assert len(result[0].holes) == 2
    assert result[0].holes == [[(float(x), float(y)) for x, y in hole] for hole in holes]


@pytest.mark.unit
def test_multipolygon_preserves_each_part_and_its_holes():
    exterior_a = _ring(0, 0, 10, 10)
    hole_a = _ring(2, 2, 3, 3)
    exterior_b = _ring(20, 20, 40, 40)
    hole_b = _ring(22, 22, 24, 24)
    hole_c = _ring(31, 31, 35, 35)

    result = parse_feature_for_all_polygon_rings(
        _feature(
            "MultiPolygon",
            [
                [exterior_a, hole_a],
                [exterior_b, hole_b, hole_c],
            ],
        )
    )

    assert len(result) == 2
    assert [len(part.holes) for part in result] == [1, 2]

    assert result[0].exterior == [(float(x), float(y)) for x, y in exterior_a]
    assert result[0].holes[0] == [(float(x), float(y)) for x, y in hole_a]

    assert result[1].exterior == [(float(x), float(y)) for x, y in exterior_b]
    assert result[1].holes[0] == [(float(x), float(y)) for x, y in hole_b]
    assert result[1].holes[1] == [(float(x), float(y)) for x, y in hole_c]


@pytest.mark.unit
def test_exterior_ring_helper_ignores_holes():
    exterior = _ring(0, 0, 10, 10)
    hole = _ring(2, 2, 4, 4)

    result = parse_feature_polygon_exterior_rings(_feature("Polygon", [exterior, hole]))

    assert len(result) == 1
    assert result[0] == [(float(x), float(y)) for x, y in exterior]


@pytest.mark.unit
def test_positions_convert_to_float_and_ignore_extra_dimensions():
    assert positions_to_xy_ring([[1, 2, 3], ["4", "5", 6], [7]]) == [(1.0, 2.0), (4.0, 5.0)]


@pytest.mark.unit
def test_feature_collection_rejects_wrong_root_type():
    with pytest.raises(ValueError, match="FeatureCollection"):
        ensure_feature_collection({"type": "Feature"})


@pytest.mark.unit
def test_feature_identifier_uses_fallback_when_missing():
    assert feature_identifier({"type": "Feature"}, fallback="feature_0") == "feature_0"


@pytest.mark.unit
def test_non_polygon_geometry_produces_no_polygons():
    result = parse_feature_for_all_polygon_rings(_feature("Point", [1, 2]))

    assert result == []


@pytest.mark.unit
def test_polygon_with_invalid_exterior_is_skipped():
    degenerate_exterior = [[0, 0], [1, 0], [0, 0]]

    result = parse_feature_for_all_polygon_rings(_feature("Polygon", [degenerate_exterior, _ring(0, 0, 1, 1)]))

    assert result == []


@pytest.mark.unit
def test_multipolygon_skips_empty_and_invalid_parts():
    valid = _ring(0, 0, 10, 10)

    result = parse_feature_for_all_polygon_rings(
        _feature("MultiPolygon", [[], [[[0, 0], [1, 1]]], "not-a-polygon", [valid]])
    )

    assert len(result) == 1
    assert result[0].exterior == [(float(x), float(y)) for x, y in valid]
    assert result[0].holes == []


@pytest.mark.unit
def test_degenerate_holes_are_dropped():
    exterior = _ring(0, 0, 10, 10)
    hole = _ring(2, 2, 4, 4)

    result = parse_feature_for_all_polygon_rings(_feature("Polygon", [exterior, [[1, 1], [2, 2]], hole]))

    assert len(result) == 1
    assert result[0].holes == [[(float(x), float(y)) for x, y in hole]]


@pytest.mark.unit
def test_transform_polygon_rings_drops_closing_vertex_and_keeps_holes():
    polygon = parse_feature_for_all_polygon_rings(_feature("Polygon", [_ring(0, 0, 10, 10), _ring(2, 2, 4, 4)]))[0]

    result = transform_polygon_rings(polygon, None)

    assert result is not None
    assert len(result.exterior) == 4
    assert len(result.holes) == 1
    assert len(result.holes[0]) == 4
