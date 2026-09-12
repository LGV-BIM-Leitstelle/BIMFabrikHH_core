"""Tests for the tree-processing helpers and the refactored record-builder apps.

These cover the pure pieces that don't require a full IFC environment:
height resolution, DataFrame → records, pset templates and domain
validation. A smoke test asserts that ``TreesBasicApp.build_ifc`` handles
the empty-records case without crashing.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from BIMFabrikHH_core.apps.trees import processing as trees_processing
from BIMFabrikHH_core.apps.trees import (
    TreeRecord,
    TreesBasicApp,
    build_tree_psets,
    calculate_tree_height,
    dataframe_to_records,
    drape_records_on_dgm,
    full_tree_height,
    tree_crown_detail_from_containers,
    tree_log_from_containers,
    validate_tree_records,
)
from BIMFabrikHH_core.apps.trees.processing import (
    CROWN_TO_HEIGHT_RATIO,
    DEFAULT_TREE_LOG,
    MIN_TREE_HEIGHT_M,
    resolve_tree_dimensions,
)
from BIMFabrikHH_core.data_models.params_tree import Component, Container
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

# ---------------------------------------------------------------------------
# calculate_tree_height
# ---------------------------------------------------------------------------


def test_calculate_tree_height_uses_measured_value_when_provided() -> None:
    h, remark = calculate_tree_height(kronendurchmesser=6.0, baumhoehe=12.0)
    assert h == 12.0
    assert "Gemessene" in remark


def test_calculate_tree_height_falls_back_to_crown_ratio() -> None:
    h, remark = calculate_tree_height(kronendurchmesser=10.0, baumhoehe=None)
    assert h == pytest.approx(CROWN_TO_HEIGHT_RATIO * 10.0)
    assert "Kronendurchmesser" in remark


def test_calculate_tree_height_enforces_minimum_height() -> None:
    h, remark = calculate_tree_height(kronendurchmesser=0.5, baumhoehe=None)
    assert h == MIN_TREE_HEIGHT_M
    assert "Mindest" in remark


# ---------------------------------------------------------------------------
# build_tree_psets
# ---------------------------------------------------------------------------


def test_build_tree_psets_returns_both_pydantic_models() -> None:
    psets = build_tree_psets(
        baumnummer="1",
        gattung="Eiche",
        art="Stieleiche",
        pflanzjahr=1990,
        kronendurchmesser_m=6.0,
        stammdurchmesser_m=0.4,
        baumhoehe_m=9.5,
        baumhoehe_bemerkung="test",
        aufnahmedatum="2026-04-01",
        strasse="Teststrasse",
    )
    assert set(psets) == {"Pset_Objektinformation", "Pset_Bauwerk"}
    assert isinstance(psets["Pset_Objektinformation"], Pset_Objektinformation_Tree)
    assert isinstance(psets["Pset_Bauwerk"], Pset_Bauwerk_Tree)


def test_build_tree_psets_accepts_none_stammdurchmesser() -> None:
    psets = build_tree_psets(
        baumnummer="2",
        gattung="Linde",
        art="Winter-Linde",
        pflanzjahr=1985,
        kronendurchmesser_m=4.0,
        stammdurchmesser_m=None,
        baumhoehe_m=3.5,
        baumhoehe_bemerkung="fallback",
        aufnahmedatum="undefiniert",
    )
    assert psets["Pset_Objektinformation"].stammdurchmesser is None


# ---------------------------------------------------------------------------
# dataframe_to_records
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Easting": 558406.01,
                "Northing": 5927514.51,
                "Elevation": 5.2,
                "kronendurchmesser": 8.0,
                "stammumfang": 157.0,
                "baumnummer": "Demo-1",
                "gattung_deutsch": "Ahorn",
                "art_deutsch": "Spitz-Ahorn",
                "strasse": "Musterweg",
                "stadtteil": "Demo-Stadtteil",
                "bezirk": "Demo-Bezirk",
                "pflanzjahr": 1990,
            }
        ]
    )


def test_dataframe_to_records_builds_one_record_per_row(sample_df: pd.DataFrame) -> None:
    records = dataframe_to_records(sample_df, aufnahmedatum="2026-04-01", source_name="unit-test")
    assert len(records) == 1
    rec = records[0]
    assert rec.position == (558406.01, 5927514.51, 5.2)
    assert rec.kronendurchmesser == 8.0
    # 157 cm → ~0.4997 m diameter.
    assert rec.stammdurchmesser == pytest.approx(157.0 / math.pi / 100.0, rel=1e-6)
    assert rec.baumhoehe is not None and rec.baumhoehe > 0


def test_dataframe_to_records_attaches_both_psets(sample_df: pd.DataFrame) -> None:
    records = dataframe_to_records(sample_df, aufnahmedatum="2026-04-01")
    psets = records[0].psets
    assert set(psets) == {"Pset_Objektinformation", "Pset_Bauwerk"}


def test_dataframe_to_records_handles_empty() -> None:
    assert dataframe_to_records(pd.DataFrame(), aufnahmedatum="undefiniert") == []


# ---------------------------------------------------------------------------
# tree_crown_detail_from_containers
# ---------------------------------------------------------------------------


def test_tree_crown_detail_defaults_when_no_containers() -> None:
    assert tree_crown_detail_from_containers(None) == 1
    assert tree_crown_detail_from_containers([]) == 1


def test_tree_crown_detail_reads_ogc_container() -> None:
    containers = [
        Container(
            containerId="level_of_geometry",
            components={"level_of_geom": Component(title="level_of_geom", value=3)},
        )
    ]
    assert tree_crown_detail_from_containers(containers) == 3


def test_tree_crown_detail_clamps_to_max_four() -> None:
    containers = [
        Container(
            containerId="level_of_geometry",
            components={"level_of_geom": Component(title="level_of_geom", value=9)},
        )
    ]
    assert tree_crown_detail_from_containers(containers) == 4


# ---------------------------------------------------------------------------
# tree_log_from_containers
# ---------------------------------------------------------------------------


def _lod_containers(value: int) -> list[Container]:
    return [
        Container(
            containerId="level_of_geometry",
            components={"level_of_geom": Component(title="level_of_geom", value=value)},
        )
    ]


def test_tree_log_defaults_to_200_without_containers() -> None:
    """An absent level must not collapse onto the extractor's LoD-1 fallback."""
    assert tree_log_from_containers(None) == DEFAULT_TREE_LOG
    assert tree_log_from_containers([]) == DEFAULT_TREE_LOG


@pytest.mark.parametrize(("lod", "expected"), [(1, 100), (2, 200), (3, 300)])
def test_tree_log_scales_the_requested_lod(lod: int, expected: int) -> None:
    assert tree_log_from_containers(_lod_containers(lod)) == expected


def test_tree_log_clamps_out_of_range_lod() -> None:
    assert tree_log_from_containers(_lod_containers(9)) == 400


def test_psets_carry_the_default_log_and_loi() -> None:
    objekt = build_tree_psets(
        baumnummer="1",
        gattung="Eiche",
        art="Quercus robur",
        pflanzjahr=1990,
        kronendurchmesser_m=6.0,
        stammdurchmesser_m=0.6,
        baumhoehe_m=24.0,
        baumhoehe_bemerkung="Gesamthöhe",
        aufnahmedatum="2026-09-12",
    )["Pset_Objektinformation"]
    dumped = objekt.model_dump(by_alias=True)
    assert (dumped["_LoG"], dumped["_LoI"]) == (200, 300)
    assert dumped["_Bemerkung"] == "undefiniert"


# ---------------------------------------------------------------------------
# validate_tree_records
# ---------------------------------------------------------------------------


def _valid_record(**overrides) -> TreeRecord:
    defaults = dict(
        name="T",
        position=(0.0, 0.0, 0.0),
        kronendurchmesser=5.0,
        stammdurchmesser=0.3,
        detail=1,
        segments=8,
        baumhoehe=10.0,
    )
    defaults.update(overrides)
    return TreeRecord(**defaults)


def test_validate_tree_records_passes_for_reasonable_records() -> None:
    validate_tree_records([_valid_record(), _valid_record(name="T2")])


def test_validate_tree_records_rejects_out_of_range_crown() -> None:
    with pytest.raises(ValueError):
        validate_tree_records([_valid_record(kronendurchmesser=500.0)])


def test_validate_tree_records_rejects_bad_detail() -> None:
    with pytest.raises(ValueError):
        validate_tree_records([_valid_record(detail=99)])


def test_validate_tree_records_rejects_non_finite_position() -> None:
    with pytest.raises(ValueError):
        validate_tree_records([_valid_record(position=(float("inf"), 0.0, 0.0))])


# ---------------------------------------------------------------------------
# resolve_tree_dimensions
# ---------------------------------------------------------------------------


def _treetop(record: TreeRecord) -> float:
    """Z of the highest point: the crown sphere sits centred on the trunk top."""
    dims = resolve_tree_dimensions(record)
    return dims.trunk_height + dims.crown_radius


def test_baumhoehe_is_the_trunk_height() -> None:
    """The crown is added on top, so the treetop clears baumhoehe by one crown Ø."""
    record = _valid_record(baumhoehe=18.0, kronendurchmesser=6.0)
    assert resolve_tree_dimensions(record).trunk_height == pytest.approx(21.0)
    assert _treetop(record) == pytest.approx(24.0)


@pytest.mark.parametrize("kronendurchmesser, expected_top", [(2.0, 4.5), (3.0, 5.55), (5.0, 9.25)])
def test_fallback_height_without_baumhoehe(kronendurchmesser: float, expected_top: float) -> None:
    record = _valid_record(baumhoehe=None, kronendurchmesser=kronendurchmesser)
    assert _treetop(record) == pytest.approx(expected_top)


# ---------------------------------------------------------------------------
# full_tree_height
# ---------------------------------------------------------------------------


def test_full_tree_height_matches_the_modelled_treetop() -> None:
    record = _valid_record(baumhoehe=18.0, kronendurchmesser=6.0)
    gesamt, _ = full_tree_height(record.baumhoehe, record.kronendurchmesser)
    assert gesamt == pytest.approx(_treetop(record))


def test_full_tree_height_remark_shows_only_the_sum() -> None:
    _, remark = full_tree_height(18.0, 6.0)
    assert remark == "Gesamthöhe = 18.00m Stammhöhe + 6.00m Kronendurchmesser = 24.00m"


def test_full_tree_height_is_rounded_to_centimetres() -> None:
    gesamt, remark = full_tree_height(4.071669926, 4.790199915882598)
    assert gesamt == 8.86
    assert remark == "Gesamthöhe = 4.07m Stammhöhe + 4.79m Kronendurchmesser = 8.86m"


def test_calculated_height_remark_rounds_the_crown_diameter() -> None:
    _, remark = calculate_tree_height(kronendurchmesser=4.790199915882598)
    assert remark == "0.85 × 4.79m Kronendurchmesser = 4.07m"


# ---------------------------------------------------------------------------
# drape_records_on_dgm
# ---------------------------------------------------------------------------


def test_drape_records_on_dgm_overwrites_z(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fake_sample(points_xy, tif_files, *, folder_path=None, default_elevation=0.0):
        assert list(tif_files) == ["a.tif", "b.tif"]
        assert folder_path == "/dgm"
        return np.array([12.5, 8.25], dtype=float)

    monkeypatch.setattr(trees_processing, "sample_elevations_for_points", _fake_sample)
    records = [
        _valid_record(name="A", position=(100.0, 200.0, 0.0)),
        _valid_record(name="B", position=(110.0, 210.0, 99.0)),
    ]
    draped = drape_records_on_dgm(records, ["a.tif", "b.tif"], folder_path="/dgm")
    assert draped[0].position == (100.0, 200.0, 12.5)
    assert draped[1].position == (110.0, 210.0, 8.25)
    assert records[1].position[2] == 99.0


def test_drape_records_on_dgm_empty() -> None:
    assert drape_records_on_dgm([], ["a.tif"]) == []


def test_drape_records_on_dgm_without_tiles_keeps_z() -> None:
    records = [_valid_record(position=(100.0, 200.0, 42.0))]
    assert drape_records_on_dgm(records, [])[0].position == (100.0, 200.0, 42.0)


# ---------------------------------------------------------------------------
# TreesBasicApp smoke test
# ---------------------------------------------------------------------------


def test_trees_basic_app_empty_records_returns_none() -> None:
    assert TreesBasicApp.build_ifc([]) is None
