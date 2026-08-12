"""
Benchmark: ``TerrainBasicApp`` vs ``TerrainGenericApp`` (same mesh, same psets).

Both apps consume the **same** :class:`TerrainMesh`. The only difference
is the IFC-writing pipeline:

- ``TerrainBasicApp``: direct ``ifcopenshell.api`` (``root.create_entity``
  + ``geometry.add_mesh_representation`` + ``pset.add_pset``).
- ``TerrainGenericApp``: ``ifcfactory.BIMFactoryElement`` (``MeshRepresentation``
  wrapped in ``Style`` + native ``PropertySetTemplate`` attach).

Writes ``perf_basic_dgm.ifc`` and ``perf_generic_dgm.ifc`` next to this
script, prints a timing / size comparison, then validates each IFC file
via ``python -m ifcopenshell.validate --rules``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Tuple

from BIMFabrikHH_core.apps.terrain import (
    TerrainBasicApp,
    TerrainGenericApp,
    TerrainMesh,
    extract_mesh_adaptive,
)
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.model_creator import validate_ifc
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams

logger = get_logger()

# Adaptive-sampling knobs (kept identical for both apps).
_MIN_POINTS: int = 500
_IMPORTANCE_THRESHOLD: float = 0.05
_MOVE_TO_ORIGIN: bool = False


def _make_request_params() -> RequestParams:
    """Minimal request params describing the DGM container."""
    container = Container(
        containerTitle="DGM_Bench",
        containerId="dgm_bench",
        components={
            "description": Component(
                title="Description",
                value="Basic vs Generic DGM benchmark",
            )
        },
    )
    return RequestParams(bbox=None, containers=[container])


def _fmt_s(x: float | None) -> str:
    return "—" if x is None else f"{x:.3f}"


def _fmt_kb(path: Path) -> str:
    if not path.exists():
        return "—"
    return f"{path.stat().st_size / 1024.0:.1f}"


def _pct_vs_basic(basic_s: float, gen_s: float) -> str:
    if basic_s <= 0:
        return "—"
    return f"{(gen_s / basic_s) * 100.0:.1f}%"


def _print_comparison(
    mesh: TerrainMesh,
    path_basic: Path,
    path_generic: Path,
    wall_basic: float,
    wall_generic: float,
) -> None:
    """Print aligned mesh summary + wall-time / file-size comparison."""
    n_vertices = len(mesh.vertices)
    n_faces = len(mesh.faces)

    logger.info("")
    logger.info(f"Mesh (shared): {n_vertices} vertices, {n_faces} faces")
    logger.info("")

    rows: List[Tuple[str, str, str, str]] = [
        (
            "Wall time (s)",
            _fmt_s(wall_basic),
            _fmt_s(wall_generic),
            _pct_vs_basic(wall_basic, wall_generic),
        ),
        (
            "IFC file size (KB)",
            _fmt_kb(path_basic),
            _fmt_kb(path_generic),
            "—",
        ),
    ]

    label_w = max(len(r[0]) for r in rows)
    col_b, col_g, col_pct = 14, 14, 12
    sep = f"{'-' * label_w}  {'-' * col_b}  {'-' * col_g}  {'-' * col_pct}"

    logger.info(f"{'Metric':<{label_w}}  {'Basic':>{col_b}}  {'Generic':>{col_g}}  {'% vs basic':>{col_pct}}")
    logger.info("  (<100% = generic faster / smaller; applies to wall time only)")
    logger.info(sep)
    for label, b, g, pct in rows:
        logger.info(f"{label:<{label_w}}  {b:>{col_b}}  {g:>{col_g}}  {pct:>{col_pct}}")
    logger.info("")


def main() -> None:
    here = Path(__file__).resolve().parent
    path_basic = here / "perf_basic_dgm.ifc"
    path_generic = here / "perf_generic_dgm.ifc"

    tif_files = [str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")]

    logger.info(f"Benchmark: DGM basic vs generic (IFC in {here})")
    logger.info(
        "  Basic:   TerrainBasicApp   (ifcopenshell.api)\n"
        "  Generic: TerrainGenericApp (ifcfactory BIMFactoryElement)"
    )

    # Build the mesh once and reuse it for both apps, so the IFC-writing
    # pipeline is the only thing being compared.
    mesh = extract_mesh_adaptive(
        tif_files,
        min_points=_MIN_POINTS,
        importance_threshold=_IMPORTANCE_THRESHOLD,
        bbox_utm=None,
        move_to_origin=_MOVE_TO_ORIGIN,
    )
    if mesh.is_empty():
        logger.warning("No valid terrain data to convert; aborting benchmark.")
        return

    request_params = _make_request_params()

    t0 = time.perf_counter()
    _ = TerrainBasicApp.build_ifc(
        mesh,
        request_params=request_params,
        output_path=path_basic,
    )
    wall_basic = time.perf_counter() - t0

    t0 = time.perf_counter()
    _ = TerrainGenericApp.build_ifc(
        mesh,
        request_params=request_params,
        output_path=path_generic,
    )
    wall_generic = time.perf_counter() - t0

    for path in (path_basic, path_generic):
        if path.exists():
            validate_ifc(path)

    _print_comparison(mesh, path_basic, path_generic, wall_basic, wall_generic)
    logger.info(f"IFC: {path_basic.name} | {path_generic.name}")


if __name__ == "__main__":
    setup_logging()
    main()
