"""Tests for the tree-processing helpers and the refactored record-builder apps.

These cover the pure pieces that don't require a full IFC environment:
height resolution, DataFrame → records, pset templates and domain
validation. A smoke test asserts that ``TreesBasicApp.build_ifc`` handles
the empty-records case without crashing.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from BIMFabrikHH_core.apps.trees import (
    TreeRecord,
    TreesBasicApp,
    build_tree_psets,
    calculate_tree_height,
    dataframe_to_records,
    validate_tree_records,
)
from BIMFabrikHH_core.apps.trees.processing import CROWN_TO_HEIGHT_RATIO, MIN_TREE_HEIGHT_M
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
# TreesBasicApp smoke test
# ---------------------------------------------------------------------------


def test_trees_basic_app_empty_records_returns_none() -> None:
    assert TreesBasicApp.build_ifc([]) is None
