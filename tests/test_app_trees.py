"""Tests for the tree-processing helpers and the refactored record-builder apps.

The pure pieces (height resolution, DataFrame → records, pset templates,
domain validation) are tested directly. The IFC tests build small models
with ``TreesGenericApp`` / ``TreesBasicApp`` and read them back.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np
import pandas as pd
import pytest

from BIMFabrikHH_core.apps.trees import processing as trees_processing
from BIMFabrikHH_core.apps.trees import (
    TreeRecord,
    TreesBasicApp,
    TreesGenericApp,
    build_tree_psets,
    calculate_tree_trunk_height,
    dataframe_to_records,
    drape_records_on_dgm,
    full_tree_height,
    tree_crown_detail_from_containers,
    tree_log_from_containers,
    validate_tree_records,
)
from BIMFabrikHH_core.apps.trees.processing import (
    DEFAULT_TREE_LOG,
    MIN_TREE_HEIGHT_M,
    TRUNK_HEIGHT_TO_CROWN_RATIO,
    resolve_tree_dimensions,
)
from BIMFabrikHH_core.data_models.params_tree import Component, Container
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

# ---------------------------------------------------------------------------
# calculate_tree_trunk_height
# ---------------------------------------------------------------------------


def test_calculate_tree_trunk_height_uses_measured_value_when_provided() -> None:
    h, remark = calculate_tree_trunk_height(kronendurchmesser=6.0, stammhoehe=12.0)
    assert h == 12.0
    assert remark == "Stammhöhe 12.00m (gemessen)"


def test_calculate_tree_trunk_height_falls_back_to_crown_ratio() -> None:
    h, remark = calculate_tree_trunk_height(kronendurchmesser=10.0, stammhoehe=None)
    assert h == pytest.approx(TRUNK_HEIGHT_TO_CROWN_RATIO * 10.0)
    assert "Kronendurchmesser" in remark


def test_calculate_tree_trunk_height_enforces_minimum_height() -> None:
    h, remark = calculate_tree_trunk_height(kronendurchmesser=0.5, stammhoehe=None)
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


def _objekt(record: TreeRecord) -> dict:
    dumped = record.psets["Pset_Objektinformation"].model_dump(by_alias=True)
    return {k: getattr(v, "magnitude", v) for k, v in dumped.items()}


def test_dataframe_to_records_uses_defaults_for_missing_and_invalid_values(sample_df: pd.DataFrame) -> None:
    df = sample_df.assign(kronendurchmesser=[float("nan")], stammumfang=["abc"], pflanzjahr=[None])
    rec = dataframe_to_records(df, aufnahmedatum="2026-04-01")[0]
    assert rec.kronendurchmesser == trees_processing.DEFAULT_KRONENDURCHMESSER_M
    assert rec.stammdurchmesser == pytest.approx(trees_processing.DEFAULT_STAMMUMFANG_CM / math.pi / 100.0, rel=1e-6)
    assert _objekt(rec)["_Pflanzjahr"] == 9999


@pytest.mark.parametrize("baumhoehe", [float("nan"), None, "abc"])
def test_dataframe_to_records_estimates_missing_or_invalid_baumhoehe(sample_df: pd.DataFrame, baumhoehe) -> None:
    rec = dataframe_to_records(sample_df.assign(baumhoehe=[baumhoehe]), aufnahmedatum="2026-04-01")[0]
    assert rec.baumhoehe == pytest.approx(6.8)
    assert _objekt(rec)["_Baumhoehe"] == pytest.approx(14.8)
    assert _objekt(rec)["_BaumhoeheBemerkung"] == (
        "Stammhöhe 6.80m (geschätzt: 0.85 × Kronendurchmesser) + Kronendurchmesser 8.00m"
    )


def test_dataframe_to_records_publishes_the_gesamthoehe_of_a_measured_trunk(sample_df: pd.DataFrame) -> None:
    rec = dataframe_to_records(sample_df.assign(baumhoehe=["8.85"]), aufnahmedatum="2026-04-01")[0]
    assert rec.baumhoehe == pytest.approx(8.85)
    assert _objekt(rec)["_Baumhoehe"] == pytest.approx(16.85)
    assert _objekt(rec)["_BaumhoeheBemerkung"] == "Stammhöhe 8.85m (gemessen) + Kronendurchmesser 8.00m"


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


@pytest.mark.parametrize(
    "overrides",
    [
        {"stammdurchmesser": -0.1},
        {"stammdurchmesser": 6.0},
        {"baumhoehe": 0.0},
        {"baumhoehe": 151.0},
        {"segments": 2},
    ],
)
def test_validate_tree_records_rejects_out_of_range_values(overrides: dict) -> None:
    with pytest.raises(ValueError):
        validate_tree_records([_valid_record(**overrides)])


def test_validate_tree_records_accepts_missing_baumhoehe() -> None:
    validate_tree_records([_valid_record(baumhoehe=None)])


# ---------------------------------------------------------------------------
# resolve_tree_dimensions
# ---------------------------------------------------------------------------


def _treetop(record: TreeRecord) -> float:
    """Z of the highest point: the crown sphere sits centred on the trunk top."""
    dims = resolve_tree_dimensions(record)
    return dims.trunk_cylinder_height + dims.crown_radius


def test_baumhoehe_is_the_trunk_height() -> None:
    """The cylinder reaches the crown centre, so the treetop clears baumhoehe by one crown Ø."""
    record = _valid_record(baumhoehe=18.0, kronendurchmesser=6.0)
    assert resolve_tree_dimensions(record).trunk_cylinder_height == pytest.approx(21.0)
    assert _treetop(record) == pytest.approx(24.0)


@pytest.mark.parametrize("kronendurchmesser, expected_top", [(2.0, 3.7), (3.0, 5.55), (5.0, 9.25)])
def test_fallback_height_without_baumhoehe(kronendurchmesser: float, expected_top: float) -> None:
    record = _valid_record(baumhoehe=None, kronendurchmesser=kronendurchmesser)
    assert _treetop(record) == pytest.approx(expected_top)


@pytest.mark.parametrize("kronendurchmesser", [0.5, 2.0, 3.0, 9.0])
def test_fallback_matches_the_published_gesamthoehe(kronendurchmesser: float) -> None:
    """Records without baumhoehe use the same trunk estimate as calculate_tree_trunk_height."""
    stammhoehe, _ = calculate_tree_trunk_height(kronendurchmesser)
    gesamthoehe, _ = full_tree_height(stammhoehe, kronendurchmesser)
    record = _valid_record(baumhoehe=None, kronendurchmesser=kronendurchmesser)
    assert _treetop(record) == pytest.approx(gesamthoehe, abs=0.01)


# ---------------------------------------------------------------------------
# full_tree_height
# ---------------------------------------------------------------------------


def test_full_tree_height_matches_the_modelled_treetop() -> None:
    record = _valid_record(baumhoehe=18.0, kronendurchmesser=6.0)
    gesamt, _ = full_tree_height(record.baumhoehe, record.kronendurchmesser)
    assert gesamt == pytest.approx(_treetop(record))


def test_full_tree_height_remark_is_the_sum() -> None:
    _, remark = full_tree_height(18.0, 6.0)
    assert remark == "Stammhöhe 18.00m + Kronendurchmesser 6.00m"


def test_full_tree_height_is_rounded_to_centimetres() -> None:
    gesamt, remark = full_tree_height(4.071669926, 4.790199915882598)
    assert gesamt == 8.86
    assert remark == "Stammhöhe 4.07m + Kronendurchmesser 4.79m"


def test_full_tree_height_remark_shows_the_estimated_trunk_height() -> None:
    stammhoehe, stammhoehe_remark = calculate_tree_trunk_height(kronendurchmesser=9.0)
    gesamt, remark = full_tree_height(stammhoehe, 9.0, stammhoehe_remark)
    assert gesamt == 16.65
    assert remark == "Stammhöhe 7.65m (geschätzt: 0.85 × Kronendurchmesser) + Kronendurchmesser 9.00m"


def test_full_tree_height_remark_shows_the_measured_trunk_height() -> None:
    stammhoehe, stammhoehe_remark = calculate_tree_trunk_height(kronendurchmesser=9.56, stammhoehe=8.85)
    gesamt, remark = full_tree_height(stammhoehe, 9.56, stammhoehe_remark)
    assert gesamt == 18.41
    assert remark == "Stammhöhe 8.85m (gemessen) + Kronendurchmesser 9.56m"


def test_calculated_height_remark_rounds_the_trunk_height() -> None:
    _, remark = calculate_tree_trunk_height(kronendurchmesser=4.790199915882598)
    assert remark == "Stammhöhe 4.07m (geschätzt: 0.85 × Kronendurchmesser)"


@pytest.mark.parametrize(
    "kwargs",
    [{"kronendurchmesser": 0.5}, {"kronendurchmesser": 6.0, "stammhoehe": 0.5}],
)
def test_trunk_height_remark_marks_the_minimum_height(kwargs: dict) -> None:
    _, remark = calculate_tree_trunk_height(**kwargs)
    assert remark == "Stammhöhe 1.10m (Mindesthöhe)"


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
# TreesGenericApp
# ---------------------------------------------------------------------------


def _psets_for(stammhoehe: float, kronendurchmesser: float) -> dict:
    gesamthoehe, remark = full_tree_height(stammhoehe, kronendurchmesser)
    return build_tree_psets(
        baumnummer="1",
        gattung="Eiche",
        art="Quercus robur",
        pflanzjahr=1990,
        kronendurchmesser_m=kronendurchmesser,
        stammdurchmesser_m=0.4,
        baumhoehe_m=gesamthoehe,
        baumhoehe_bemerkung=remark,
        aufnahmedatum="2026-04-01",
    )


def _proxies(path: Path) -> dict:
    model = ifcopenshell.open(str(path))
    return {e.Name: e for e in model.by_type("IfcBuildingElementProxy")}


def _z_range(product) -> tuple[float, float]:
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    # Keep ``shape`` alive while reading: ``verts`` views memory owned by it.
    shape = ifcopenshell.geom.create_shape(settings, product)
    verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3)
    return float(verts[:, 2].min()), float(verts[:, 2].max())


def _items(product) -> list:
    return [item for rep in product.Representation.Representations for item in rep.Items]


def test_trees_generic_app_writes_one_proxy_per_record(tmp_path: Path) -> None:
    records = [
        _valid_record(name="Baum_A", position=(100.0, 200.0, 5.0)),
        _valid_record(name="Baum_B", position=(110.0, 200.0, 5.0)),
    ]
    written = TreesGenericApp.build_ifc(records, output_path=tmp_path / "trees.ifc", name_prefix="SBK_")
    assert written == tmp_path / "trees.ifc"
    assert set(_proxies(written)) == {"SBK_Baum_A", "SBK_Baum_B"}


def test_trees_generic_app_treetop_is_the_published_baumhoehe(tmp_path: Path) -> None:
    """Crown detail 2 has vertices at the poles, so the mesh reaches the exact sphere top."""
    record = _valid_record(
        name="Baum_A",
        position=(100.0, 200.0, 5.0),
        kronendurchmesser=6.0,
        baumhoehe=18.0,
        detail=2,
        psets=_psets_for(18.0, 6.0),
    )
    tree = _proxies(TreesGenericApp.build_ifc([record], output_path=tmp_path / "trees.ifc"))["Baum_A"]
    objekt = ifcopenshell.util.element.get_psets(tree)["Pset_Objektinformation"]
    base, top = _z_range(tree)
    assert objekt["_Baumhoehe"] == pytest.approx(24.0)
    assert base == pytest.approx(5.0)
    assert top - base == pytest.approx(objekt["_Baumhoehe"], abs=0.01)
    assert len(_items(tree)) == 2


def test_trees_generic_app_attaches_psets_only_when_requested(tmp_path: Path) -> None:
    record = _valid_record(name="Baum_A", psets=_psets_for(10.0, 5.0))
    with_psets = _proxies(TreesGenericApp.build_ifc([record], output_path=tmp_path / "a.ifc"))["Baum_A"]
    without = _proxies(
        TreesGenericApp.build_ifc([record], output_path=tmp_path / "b.ifc", include_property_sets=False)
    )["Baum_A"]
    assert set(ifcopenshell.util.element.get_psets(with_psets)) == {"Pset_Objektinformation", "Pset_Bauwerk"}
    assert ifcopenshell.util.element.get_psets(without) == {}


@pytest.mark.parametrize(("baumhoehe", "expected_height"), [(None, 0.5), (0.8, 0.8)])
def test_trees_generic_app_models_a_stump_as_trunk_only(
    tmp_path: Path, baumhoehe: float | None, expected_height: float
) -> None:
    record = _valid_record(name="Stumpf_001", position=(100.0, 200.0, 5.0), baumhoehe=baumhoehe, is_stump=True)
    stump = _proxies(TreesGenericApp.build_ifc([record], output_path=tmp_path / "stump.ifc"))["Stumpf_001"]
    base, top = _z_range(stump)
    assert len(_items(stump)) == 1
    assert top - base == pytest.approx(expected_height)


def test_trees_generic_app_assigns_trunk_and_crown_layers(tmp_path: Path) -> None:
    records = [_valid_record(name="Baum_A"), _valid_record(name="Stumpf_001", is_stump=True)]
    path = TreesGenericApp.build_ifc(
        records, output_path=tmp_path / "trees.ifc", trunk_layer="Stamm", crown_layer="Krone"
    )
    layers = {
        la.Name: len(la.AssignedItems) for la in ifcopenshell.open(str(path)).by_type("IfcPresentationLayerAssignment")
    }
    assert layers == {"Stamm": 2, "Krone": 1}


# ---------------------------------------------------------------------------
# TreesBasicApp (deprecated)
# ---------------------------------------------------------------------------


def test_trees_basic_app_empty_records_returns_none() -> None:
    assert TreesBasicApp.build_ifc([]) is None


def test_trees_basic_app_writes_trees_with_psets(tmp_path: Path) -> None:
    records = [
        _valid_record(name="Baum_A", position=(100.0, 200.0, 5.0), psets=_psets_for(18.0, 6.0)),
        _valid_record(name="Baum_B", position=(110.0, 200.0, 5.0)),
    ]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        written = TreesBasicApp.build_ifc(records, output_path=tmp_path / "basic.ifc")
    proxies = _proxies(written)
    assert {"Baum_A", "Baum_B"} <= set(proxies)
    assert ifcopenshell.util.element.get_psets(proxies["Baum_A"])["Pset_Objektinformation"]["_Baumhoehe"] == 24.0
    assert ifcopenshell.util.element.get_psets(proxies["Baum_B"]) == {}


def test_trees_basic_app_is_deprecated(tmp_path: Path) -> None:
    with pytest.warns(DeprecationWarning):
        TreesBasicApp.build_ifc([_valid_record()], output_path=tmp_path / "basic.ifc")
