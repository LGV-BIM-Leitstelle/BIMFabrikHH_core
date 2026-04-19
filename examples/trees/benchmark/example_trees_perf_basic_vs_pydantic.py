"""
Benchmark: ``BaumModeller`` vs ``BaumPydanticApp`` (same synthetic trees, both with psets).

Writes ``perf_basic_{n}_trees.ifc`` and ``perf_pydantic_{n}_trees.ifc`` next to this script,
prints phase timings, then runs ``python -m ifcopenshell.validate --rules`` on each file.

"""

from __future__ import annotations

import contextlib
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import ifcopenshell.api.pset as ifc_pset
import pandas as pd
from ifcfactory import ureg

from BIMFabrikHH_core.apps.trees.basic.app import BaumModeller
from BIMFabrikHH_core.apps.trees.generic.app_pydantic import BaumPydanticApp
from BIMFabrikHH_core.data_models.params_tree import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

# WGS84 bbox (Hamburg area); same pattern as ``example_basic_trees.py``.
_BBOX = BoundingBoxParams(min_x=9.877815, min_y=53.492363, max_x=9.887343, max_y=53.496003)

_CONTAINER = Container(
    containerTitle="Trees_Container",
    containerId="trees_perf",
    components={
        "description": Component(title="Description", value="Perf benchmark"),
        "type": Component(title="Data Type", value="Tree Inventory"),
    },
)
_REQUEST = RequestParams(bbox=_BBOX, containers=[_CONTAINER])

# Grid origin / step (EPSG:25832 metres, same scale as other tree examples).
_E0 = 558_400.0
_N0 = 5_927_500.0
_GRID_COLS = 10
_STEP_M = 4.0

# Number of trees for both pipelines (no CLI — change here to benchmark a different size).
TREE_COUNT = 100


@contextlib.contextmanager
def _time_ifc_pset_api_seconds() -> Generator[List[float], None, None]:
    """Accumulate wall time spent inside ifcopenshell ``add_pset`` / ``edit_pset`` (benchmark only)."""
    acc = [0.0]
    orig_add = ifc_pset.add_pset
    orig_edit = ifc_pset.edit_pset

    def add_pset(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig_add(*args, **kwargs)
        finally:
            acc[0] += time.perf_counter() - t0

    def edit_pset(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig_edit(*args, **kwargs)
        finally:
            acc[0] += time.perf_counter() - t0

    ifc_pset.add_pset = add_pset  # type: ignore[assignment]
    ifc_pset.edit_pset = edit_pset  # type: ignore[assignment]
    try:
        yield acc
    finally:
        ifc_pset.add_pset = orig_add  # type: ignore[assignment]
        ifc_pset.edit_pset = orig_edit  # type: ignore[assignment]


def _psets_for_basic_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Pydantic psets aligned with ``baum_manager.place_trees_from_df`` / basic DataFrame fields."""
    stammumfang = float(row["stammumfang"])
    stammdurchmesser_m = max(0.05, stammumfang / math.pi)
    kd = float(row["kronendurchmesser"])
    pj = int(row["pflanzjahr_portal"])
    obj = Pset_Objektinformation_Tree(
        baumnummer=str(row["baumnummer"]),
        gattung_deutsch=str(row["gattung_deutsch"]),
        art_baum=str(row["art_deutsch"]),
        pflanzjahr=pj,
        kronendurchmesser=ureg.Quantity(kd, "meter"),
        stammdurchmesser=ureg.Quantity(stammdurchmesser_m, "meter"),
        stadtteil=str(row["stadtteil"]),
        bezirk=str(row["bezirk"]),
        status_vegetation="Bestand",
        log=100,
        loi=100,
        aufnahmedatum_vermessung="undefiniert",
    )
    bau = Pset_Bauwerk_Tree(strassenname=str(row["strasse"]))
    return {"Pset_Objektinformation": obj, "Pset_Bauwerk": bau}


def _make_rows(count: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (rows for basic DataFrame, rows for BaumPydanticApp) with matching positions/sizes and psets."""
    basic_rows: List[Dict[str, Any]] = []
    pydantic_rows: List[Dict[str, Any]] = []

    for i in range(count):
        col = i % _GRID_COLS
        row = i // _GRID_COLS
        easting = _E0 + col * _STEP_M
        northing = _N0 + row * _STEP_M
        elevation = 5.0 + (i % 5) * 0.05
        kronendurchmesser = 4.5 + (i % 11) * 0.1
        stammumfang = 0.9 + (i % 5) * 0.05
        stammdurchmesser = max(0.05, stammumfang / math.pi)

        sid = str(10_000 + i)
        br = {
            "kronendurchmesser": kronendurchmesser,
            "stammumfang": stammumfang,
            "Easting": easting,
            "Northing": northing,
            "Elevation": elevation,
            "baumnummer": sid,
            "baumid": sid,
            "gattung_deutsch": "Bench",
            "art_deutsch": "Species",
            "sorte_deutsch": "Sorte",
            "strasse": "Benchstrasse",
            "stadtteil": "Hamburg",
            "bezirk": "Hamburg-Mitte",
            "pflanzjahr_portal": 1990 + (i % 20),
        }
        basic_rows.append(br)
        pr: Dict[str, Any] = {
            "name": f"Bench_{i:04d}",
            "position": (easting, northing, elevation),
            "kronendurchmesser": kronendurchmesser,
            "stammdurchmesser": stammdurchmesser,
            # Align with basic defaults: OGC ``DEFAULT_LEVEL_OF_GEOMETRY`` is 1; basic trunk uses 5 segments.
            # Crown mesh still differs (icosphere vs ifcfactory Sphere) — comparable LOD numbers only.
            "detail": 1,
            "segments": 5,
            "psets": _psets_for_basic_row(br),
        }
        pydantic_rows.append(pr)

    return basic_rows, pydantic_rows


def _fmt_s(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x:.3f}"


def _fmt_pct_vs_basic(
    basic_s: float | None,
    pyd_s: float | None,
    wall_basic: float,
    wall_pyd: float,
) -> str:
    """Percentage for the last column.

    - Both sides: (pydantic / basic) × 100 (same phase; <100% = pydantic faster).
    - Pydantic only: (pydantic / basic wall) × 100 — share of basic end-to-end time.
    - Basic only: (basic / pydantic wall) × 100 — share of pydantic end-to-end time.
    """
    if pyd_s is not None and basic_s is not None and basic_s > 0:
        return f"{(pyd_s / basic_s) * 100.0:.1f}%"
    if pyd_s is not None and basic_s is None and wall_basic > 0:
        return f"{(pyd_s / wall_basic) * 100.0:.1f}%"
    if basic_s is not None and pyd_s is None and wall_pyd > 0:
        return f"{(basic_s / wall_pyd) * 100.0:.1f}%"
    return "—"


def _print_phase_table(
    basic: Dict[str, float],
    pyd: Dict[str, float],
    wall_basic: float,
    wall_pyd: float,
) -> None:
    """Print aligned table: phase vs seconds for each pipeline, plus pydantic % of basic time."""
    row_specs: List[Tuple[str, float | None, float | None]] = [
        ("Project / IFC setup (`build_project`)", basic.get("project_setup_s"), pyd.get("project_setup_s")),
        (
            "Tree geometry (basic: `create_tree` each row; pydantic: `create_tree_element` loop)",
            basic.get("tree_geometry_s"),
            pyd.get("prepare_elements_s"),
        ),
        (
            "Property sets (`add_pset` + `edit_pset` per tree)",
            basic.get("tree_pset_s"),
            pyd.get("tree_pset_s"),
        ),
        ("Batch `BIMFactoryElement.build_in` (attach all to site)", None, pyd.get("build_in_s")),
        ("Basepoint quad (`BIMFactoryElement`)", basic.get("basepoint_s"), None),
        ("Save IFC file", basic.get("save_s"), pyd.get("save_s")),
    ]

    sum_b = sum(
        basic.get(k, 0.0) for k in ("project_setup_s", "tree_geometry_s", "tree_pset_s", "basepoint_s", "save_s")
    )
    sum_p = sum(pyd.get(k, 0.0) for k in ("project_setup_s", "prepare_elements_s", "build_in_s", "save_s"))
    row_specs.append(("Sum of measured phases", sum_b, sum_p))
    row_total = ("Total (wall time, end-to-end)", wall_basic, wall_pyd)

    rows: List[Tuple[str, str, str, str]] = [
        (
            label,
            _fmt_s(bs),
            _fmt_s(ps),
            _fmt_pct_vs_basic(bs, ps, wall_basic, wall_pyd),
        )
        for label, bs, ps in row_specs
    ]
    rows.append(
        (
            row_total[0],
            _fmt_s(row_total[1]),
            _fmt_s(row_total[2]),
            _fmt_pct_vs_basic(row_total[1], row_total[2], wall_basic, wall_pyd),
        )
    )

    w = max(len(r[0]) for r in rows)
    col_b, col_p, col_pct = 14, 14, 12
    sep = f"{'-' * w}  {'-' * col_b}  {'-' * col_p}  {'-' * col_pct}"
    print()
    print(f"{'Phase':<{w}}  {'Basic (s)':>{col_b}}  {'Pydantic (s)':>{col_p}}  " f"{'% vs basic':>{col_pct}}")
    print(
        "  (row has both times: pydantic/basic × 100; pydantic-only: pydantic/basic wall × 100; "
        "basic-only: basic/pydantic wall × 100)"
    )
    print(
        "  Pydantic Property sets column: seconds from this script's ifcopenshell.api.pset timing wrapper "
        "(subset of `build_in_s`; not added again in Sum of measured phases)."
    )
    print(sep)
    for label, b, p, pct in rows[:-1]:
        print(f"{label:<{w}}  {b:>{col_b}}  {p:>{col_p}}  {pct:>{col_pct}}")
    print(sep)
    label, b, p, pct = rows[-1]
    print(f"{label:<{w}}  {b:>{col_b}}  {p:>{col_p}}  {pct:>{col_pct}}")
    print()


def main() -> None:
    count = max(1, TREE_COUNT)

    here = Path(__file__).resolve().parent
    path_basic = here / f"perf_basic_{count}_trees.ifc"
    path_pydantic = here / f"perf_pydantic_{count}_trees.ifc"

    basic_data, pydantic_data = _make_rows(count)
    df = pd.DataFrame(basic_data)

    timings_basic: Dict[str, float] = {}
    timings_pyd: Dict[str, float] = {}

    print(f"Benchmark: {count} trees (IFC in {here})")
    print(
        "  Basic: BaumModeller + per-tree Psets (add_pset/edit_pset) | "
        "Pydantic: geometry + Pset_Objektinformation / Pset_Bauwerk templates (BIMFactoryElement)"
    )
    print()

    t_wall_b0 = time.perf_counter()
    modeller = BaumModeller()
    _ = modeller.create_tree_model_from_df(
        df,
        _REQUEST,
        tif_path=None,
        use_geotiff_elevation=False,
        output_path=path_basic,
        phase_timings=timings_basic,
    )
    wall_basic = time.perf_counter() - t_wall_b0

    t_wall_p0 = time.perf_counter()
    with _time_ifc_pset_api_seconds() as pset_s:
        _ = BaumPydanticApp.build_ifc_from_tree_data(
            pydantic_data,
            output_path=path_pydantic,
            include_property_sets=True,
            phase_timings=timings_pyd,
        )
        timings_pyd["tree_pset_s"] = float(pset_s[0])
    wall_pyd = time.perf_counter() - t_wall_p0

    for path in (path_basic, path_pydantic):
        subprocess.run(
            [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(path)],
            check=True,
        )

    _print_phase_table(timings_basic, timings_pyd, wall_basic, wall_pyd)
    print(f"IFC: {path_basic.name} | {path_pydantic.name}")


if __name__ == "__main__":
    main()
