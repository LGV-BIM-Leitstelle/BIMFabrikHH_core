"""
Benchmark: ``TreesBasicApp`` vs ``TreesGenericApp`` (same synthetic trees, same psets).

Both apps consume the **same** ``list[TreeRecord]``. The only difference
is the geometry + pset attach pipeline:

- ``TreesBasicApp``: mesh trunk + icosphere crown via ``ifcopenshell.api``
  and ``pset.add_pset`` / ``pset.edit_pset``.
- ``TreesGenericApp``: ``ifcfactory.BIMFactoryElement`` (batched
  ``build_in`` + native ``PropertySetTemplate`` attach).

Writes ``perf_basic_{n}_trees.ifc`` and ``perf_generic_{n}_trees.ifc``
next to this script, prints phase timings, then validates each IFC file
via ``python -m ifcopenshell.validate --rules``.
"""

from __future__ import annotations

import contextlib
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Tuple

import ifcopenshell.api.pset as ifc_pset

from BIMFabrikHH_core.apps.trees import TreeRecord, TreesBasicApp, TreesGenericApp, build_tree_psets
from BIMFabrikHH_core.core.model_creator import validate_ifc

# Grid origin / step (EPSG:25832 metres).
_E0 = 558_400.0
_N0 = 5_927_500.0
_GRID_COLS = 10
_STEP_M = 4.0

TREE_COUNT = 100


@contextlib.contextmanager
def _time_ifc_pset_api_seconds() -> Generator[List[float], None, None]:
    """Accumulate wall time spent inside ``ifcopenshell.api.pset`` calls (benchmark-only)."""
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


def _make_records(count: int) -> List[TreeRecord]:
    """Build ``count`` synthetic tree records with full Pydantic psets."""
    records: List[TreeRecord] = []
    for i in range(count):
        col = i % _GRID_COLS
        grid_row = i // _GRID_COLS
        easting = _E0 + col * _STEP_M
        northing = _N0 + grid_row * _STEP_M
        elevation = 5.0 + (i % 5) * 0.05
        kronendurchmesser_m = 4.5 + (i % 11) * 0.1
        stammdurchmesser_m = 0.25 + (i % 5) * 0.01
        pflanzjahr = 1990 + (i % 20)

        sid = str(10_000 + i)
        psets = build_tree_psets(
            baumnummer=sid,
            gattung="Bench",
            art="Species",
            pflanzjahr=pflanzjahr,
            kronendurchmesser_m=kronendurchmesser_m,
            stammdurchmesser_m=stammdurchmesser_m,
            baumhoehe_m=1.35 * kronendurchmesser_m,
            baumhoehe_bemerkung="Benchmark synthetic height",
            aufnahmedatum="undefiniert",
            stadtteil="Hamburg",
            bezirk="Hamburg-Mitte",
            bemerkung="Perf benchmark",
            status_vegetation="Bestand",
            strasse="Benchstrasse",
        )
        records.append(
            TreeRecord(
                name=f"Bench_{i:04d}",
                position=(easting, northing, elevation),
                kronendurchmesser=kronendurchmesser_m,
                stammdurchmesser=stammdurchmesser_m,
                # Align with old basic defaults: crown LOD = 1, trunk segments = 5.
                detail=1,
                segments=5,
                psets=psets,
            )
        )

    return records


def _fmt_s(x: float | None) -> str:
    if x is None:
        return "—"
    return f"{x:.3f}"


def _fmt_pct_vs_basic(
    basic_s: float | None,
    gen_s: float | None,
    wall_basic: float,
    wall_gen: float,
) -> str:
    """Percentage for the last column.

    - Both sides: (generic / basic) × 100 (same phase; <100% = generic faster).
    - Generic only: (generic / basic wall) × 100 — share of basic end-to-end time.
    - Basic only: (basic / generic wall) × 100 — share of generic end-to-end time.
    """
    if gen_s is not None and basic_s is not None and basic_s > 0:
        return f"{(gen_s / basic_s) * 100.0:.1f}%"
    if gen_s is not None and basic_s is None and wall_basic > 0:
        return f"{(gen_s / wall_basic) * 100.0:.1f}%"
    if basic_s is not None and gen_s is None and wall_gen > 0:
        return f"{(basic_s / wall_gen) * 100.0:.1f}%"
    return "—"


def _print_phase_table(
    basic: Dict[str, float],
    gen: Dict[str, float],
    wall_basic: float,
    wall_gen: float,
) -> None:
    """Print aligned phase-timings table with generic-vs-basic percentage column."""
    row_specs: List[Tuple[str, float | None, float | None]] = [
        ("Project / IFC setup (`build_project`)", basic.get("project_setup_s"), gen.get("project_setup_s")),
        (
            "Tree geometry (basic: mesh per row; generic: `create_tree_element` loop)",
            basic.get("tree_geometry_s"),
            gen.get("prepare_elements_s"),
        ),
        (
            "Property sets (`add_pset` + `edit_pset` per tree)",
            basic.get("tree_pset_s"),
            gen.get("tree_pset_s"),
        ),
        ("Batch `BIMFactoryElement.build_in` (attach all to site)", None, gen.get("build_in_s")),
        ("Save IFC file", basic.get("save_s"), gen.get("save_s")),
    ]

    sum_b = sum(basic.get(k, 0.0) for k in ("project_setup_s", "tree_geometry_s", "tree_pset_s", "save_s"))
    sum_g = sum(gen.get(k, 0.0) for k in ("project_setup_s", "prepare_elements_s", "build_in_s", "save_s"))
    row_specs.append(("Sum of measured phases", sum_b, sum_g))
    row_total = ("Total (wall time, end-to-end)", wall_basic, wall_gen)

    rows: List[Tuple[str, str, str, str]] = [
        (label, _fmt_s(bs), _fmt_s(ps), _fmt_pct_vs_basic(bs, ps, wall_basic, wall_gen)) for label, bs, ps in row_specs
    ]
    rows.append(
        (
            row_total[0],
            _fmt_s(row_total[1]),
            _fmt_s(row_total[2]),
            _fmt_pct_vs_basic(row_total[1], row_total[2], wall_basic, wall_gen),
        )
    )

    w = max(len(r[0]) for r in rows)
    col_b, col_p, col_pct = 14, 14, 12
    sep = f"{'-' * w}  {'-' * col_b}  {'-' * col_p}  {'-' * col_pct}"
    print()
    print(f"{'Phase':<{w}}  {'Basic (s)':>{col_b}}  {'Generic (s)':>{col_p}}  {'% vs basic':>{col_pct}}")
    print(
        "  (row has both times: generic/basic × 100; generic-only: generic/basic wall × 100; "
        "basic-only: basic/generic wall × 100)"
    )
    print(
        "  Generic Property sets column: seconds from this script's ifcopenshell.api.pset timing wrapper "
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
    path_generic = here / f"perf_generic_{count}_trees.ifc"

    records = _make_records(count)

    timings_basic: Dict[str, float] = {}
    timings_gen: Dict[str, float] = {}

    print(f"Benchmark: {count} trees (IFC in {here})")
    print(
        "  Basic: TreesBasicApp (mesh + ifcopenshell.api psets) | "
        "Generic: TreesGenericApp (ifcfactory BIMFactoryElement + Pydantic psets)"
    )
    print()

    t_wall_b0 = time.perf_counter()
    _ = TreesBasicApp.build_ifc(
        records,
        output_path=path_basic,
        include_property_sets=True,
        phase_timings=timings_basic,
    )
    wall_basic = time.perf_counter() - t_wall_b0

    t_wall_p0 = time.perf_counter()
    with _time_ifc_pset_api_seconds() as pset_s:
        _ = TreesGenericApp.build_ifc(
            records,
            output_path=path_generic,
            include_property_sets=True,
            phase_timings=timings_gen,
        )
        timings_gen["tree_pset_s"] = float(pset_s[0])
    wall_gen = time.perf_counter() - t_wall_p0

    for path in (path_basic, path_generic):
        validate_ifc(path)

    _print_phase_table(timings_basic, timings_gen, wall_basic, wall_gen)
    print(f"IFC: {path_basic.name} | {path_generic.name}")


if __name__ == "__main__":
    main()
