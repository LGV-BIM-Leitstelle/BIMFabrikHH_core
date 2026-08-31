"""1 km × 1 km and 2 km × 2 km: generic vs rust (city, trees, DGM).

Same UTM crop for all three apps. Needs ``BIMFABRIKHH_DGM_TIF_DIR`` and
``BIMFABRIKHH_LOD1_GML_DIR`` (repo ``.env`` or the environment). ``/mnt/c/…``
is tried as ``C:\\…`` first, then as WSL ``/mnt``.

```bash
python examples/compare_km_generic_vs_rust.py
python examples/compare_km_generic_vs_rust.py --km 1
```
"""

from __future__ import annotations

import argparse
import os
import re
import time
from collections import Counter
from pathlib import Path

from pyproj import Transformer

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, PathConfig, RequestParams
from BIMFabrikHH_core.apps.city import CityGenericApp, CityRustApp
from BIMFabrikHH_core.apps.terrain import TerrainGenericApp, TerrainRustApp
from BIMFabrikHH_core.apps.terrain.processing import extract_mesh_adaptive
from BIMFabrikHH_core.apps.trees import TreesGenericApp, TreesRustApp
from BIMFabrikHH_core.apps.trees.processing import build_tree_psets
from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.data_models import TreeRecord

logger = get_logger()

_ROOT = Path(__file__).resolve().parents[1]
_ORIGIN = (565000.0, 5933000.0)
_SIZES = {1: 1000.0, 2: 2000.0}
_LOD1 = {
    1: ("LoD1_32_565_5933_1_HH.xml",),
    2: (
        "LoD1_32_565_5933_1_HH.xml",
        "LoD1_32_565_5934_1_HH.xml",
        "LoD1_32_566_5933_1_HH.xml",
        "LoD1_32_566_5934_1_HH.xml",
    ),
}
_DGM = {
    1: ("dgm1_32_565_9330_1_hh_2022.tif",),
    2: (
        "dgm1_32_565_9330_1_hh_2022.tif",
        "dgm1_32_565_9340_1_hh_2022.tif",
        "dgm1_32_566_9330_1_hh_2022.tif",
        "dgm1_32_566_9340_1_hh_2022.tif",
    ),
}
_TREE_GRID = {1: (10, 10), 2: (20, 20)}


def _load_dotenv() -> None:
    for path in (_ROOT / ".env", _ROOT.parent / "bimfabrikhh_core_rs" / ".env"):
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value


_MNT_DRIVE = re.compile(r"^/mnt/([a-zA-Z])(?:/(.*))?$")
_WIN_DRIVE = re.compile(r"^([a-zA-Z]):(?:[\\/](.*))?$")


def _as_windows(raw: str) -> Path | None:
    posix = raw.replace("\\", "/")
    mnt = _MNT_DRIVE.match(posix)
    if mnt:
        rest = (mnt.group(2) or "").replace("/", "\\")
        return Path(f"{mnt.group(1).upper()}:\\" + rest)
    win = _WIN_DRIVE.match(posix)
    if win:
        rest = (win.group(2) or "").replace("/", "\\")
        return Path(f"{win.group(1).upper()}:\\" + rest)
    return None


def _as_mnt(raw: str) -> Path | None:
    posix = raw.replace("\\", "/")
    mnt = _MNT_DRIVE.match(posix)
    if mnt:
        return Path(posix)
    win = _WIN_DRIVE.match(posix)
    if win:
        rest = win.group(2) or ""
        return Path(f"/mnt/{win.group(1).lower()}/{rest}")
    return None


def _resolve_dir(raw: str) -> Path | None:
    """Windows drive first (``C:\\…``), then WSL ``/mnt/c/…``."""
    seen: list[Path] = []
    for candidate in (_as_windows(raw), _as_mnt(raw), Path(raw).expanduser()):
        if candidate is None or candidate in seen:
            continue
        seen.append(candidate)
        if candidate.is_dir():
            return candidate
    return None


def _require_dir(name: str) -> Path:
    raw = os.environ.get(name, "").strip()
    if not raw:
        raise FileNotFoundError(f"{name} is not set. Add it to .env.")
    path = _resolve_dir(raw)
    if path is None:
        tried = [p for p in (_as_windows(raw), _as_mnt(raw), Path(raw).expanduser()) if p is not None]
        raise FileNotFoundError(f"{name} is not a directory (tried: {', '.join(str(p) for p in tried)})")
    return path


def _bbox_utm(km: int) -> tuple[float, float, float, float]:
    size = _SIZES[km]
    return (_ORIGIN[0], _ORIGIN[1], _ORIGIN[0] + size, _ORIGIN[1] + size)


def _bbox_wgs84(bbox_utm: tuple[float, float, float, float]) -> BoundingBoxParams:
    to_ll = Transformer.from_crs("EPSG:25832", "EPSG:4326", always_xy=True)
    min_lon, min_lat = to_ll.transform(bbox_utm[0], bbox_utm[1])
    max_lon, max_lat = to_ll.transform(bbox_utm[2], bbox_utm[3])
    return BoundingBoxParams(min_x=min_lon, min_y=min_lat, max_x=max_lon, max_y=max_lat)


def _request(bbox_utm: tuple[float, float, float, float], *, title: str, cid: str) -> RequestParams:
    return RequestParams(
        bbox=_bbox_wgs84(bbox_utm),
        containers=[
            Container(
                containerTitle=title,
                containerId=cid,
                components={"description": Component(title="Description", value=title)},
            )
        ],
    )


def _rel(path: Path) -> str:
    return os.path.relpath(path, Path.cwd())


def _tree_records(bbox: tuple[float, float, float, float], cols: int, rows: int) -> list[TreeRecord]:
    min_x, min_y, max_x, max_y = bbox
    dx = (max_x - min_x) / max(cols - 1, 1)
    dy = (max_y - min_y) / max(rows - 1, 1)
    trees = []
    n = 0
    for row in range(rows):
        for col in range(cols):
            n += 1
            name = f"Baum_{n:03d}"
            trees.append(
                TreeRecord(
                    name=name,
                    position=(min_x + col * dx, min_y + row * dy, 5.0),
                    kronendurchmesser=5.0,
                    stammdurchmesser=0.6,
                    detail=1,
                    segments=8,
                    baumhoehe=4.0,
                    psets=build_tree_psets(
                        baumnummer=name,
                        gattung="Eiche",
                        art="Quercus robur",
                        pflanzjahr=1990,
                        kronendurchmesser_m=5.0,
                        stammdurchmesser_m=0.6,
                        baumhoehe_m=4.0,
                        baumhoehe_bemerkung="grid",
                        aufnahmedatum="2022-04-30",
                        strasse="Vergleich",
                    ),
                )
            )
    return trees


def _stats(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    types = Counter(re.findall(r"=IFC([A-Z0-9]+)\(", text))
    return {
        "mb": path.stat().st_size / 1e6,
        "proxy": types.get("BUILDINGELEMENTPROXY", 0),
        "bldg": types.get("BUILDING", 0),
        "pset": types.get("PROPERTYSET", 0),
        "faceset": types.get("POLYGONALFACESET", 0) + types.get("TRIANGULATEDFACESET", 0),
    }


def _timed(fn):
    t0 = time.perf_counter()
    result = fn()
    return result, time.perf_counter() - t0


def _run_trees(km: int, bbox: tuple[float, float, float, float], out: Path) -> list[tuple]:
    cols, rows = _TREE_GRID[km]
    records = _tree_records(bbox, cols, rows)
    g_path, r_path = out / f"trees_{km}km_generic.ifc", out / f"trees_{km}km_rust.ifc"
    gp, tg = _timed(
        lambda: TreesGenericApp.build_ifc(
            records, output_path=g_path, include_property_sets=True, basepoint_origin=bbox[:2]
        )
    )
    rp, tr = _timed(
        lambda: TreesRustApp.build_ifc(
            records, output_path=r_path, include_property_sets=True, basepoint_origin=bbox[:2]
        )
    )
    logger.info("trees %dkm  %d records  generic=%.2fs rust=%.2fs", km, len(records), tg, tr)
    return [
        ("trees", km, f"{cols}×{rows} grid", "generic", tg, gp, g_path),
        ("trees", km, f"{cols}×{rows} grid", "rust", tr, rp, r_path),
    ]


def _run_terrain(km: int, bbox: tuple[float, float, float, float], out: Path, dgm_dir: Path) -> list[tuple]:
    tifs = [str(dgm_dir / name) for name in _DGM[km]]
    missing = [p for p in tifs if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError("DGM tiles missing:\n" + "\n".join(missing))
    req = _request(bbox, title="DGM_km", cid=f"dgm_{km}km")
    mesh, tm = _timed(
        lambda: extract_mesh_adaptive(
            tifs, min_points=1000, importance_threshold=0.1, bbox_utm=bbox, move_to_origin=False
        )
    )
    logger.info("terrain mesh %dkm  %.2fs  verts=%d faces=%d", km, tm, len(mesh.vertices), len(mesh.faces))
    g_path, r_path = out / f"terrain_{km}km_generic.ifc", out / f"terrain_{km}km_rust.ifc"
    gp, tg = _timed(lambda: TerrainGenericApp.build_ifc(mesh, request_params=req, output_path=g_path))
    rp, tr = _timed(lambda: TerrainRustApp.build_ifc(mesh, request_params=req, output_path=r_path))
    extra = f"{len(mesh.vertices)} verts, mesh {tm:.2f}s"
    return [
        ("terrain", km, extra, "generic", tg, gp, g_path),
        ("terrain", km, extra, "rust", tr, rp, r_path),
    ]


def _run_city(km: int, bbox: tuple[float, float, float, float], out: Path, lod1_dir: Path) -> list[tuple]:
    names = _LOD1[km]
    missing = [lod1_dir / n for n in names if not (lod1_dir / n).is_file()]
    if missing:
        raise FileNotFoundError("LoD1 tiles missing:\n" + "\n".join(str(p) for p in missing))
    rel = [_rel(lod1_dir / n) for n in names]
    abs_paths = [str(lod1_dir / n) for n in names]
    req = _request(bbox, title="City_km", cid=f"city_{km}km")
    g_path, r_path = out / f"city_{km}km_generic.ifc", out / f"city_{km}km_rust.ifc"
    gp, tg = _timed(
        lambda: CityGenericApp.from_gml_files(
            gml_files=rel, request_params=req, folder_path=None, output_path=g_path
        )
    )
    rp, tr = _timed(
        lambda: CityRustApp.from_gml_files(
            gml_files=abs_paths, request_params=req, mode="mesh", output_path=r_path
        )
    )
    logger.info("city %dkm  generic=%.2fs rust=%.2fs", km, tg, tr)
    return [
        ("city", km, f"{len(names)} LoD1 tiles", "generic", tg, gp, g_path),
        ("city", km, f"{len(names)} LoD1 tiles", "rust", tr, rp, r_path),
    ]


def main(*, kilometres: tuple[int, ...] = (1, 2)) -> None:
    _load_dotenv()
    dgm_dir = _require_dir("BIMFABRIKHH_DGM_TIF_DIR")
    lod1_dir = _require_dir("BIMFABRIKHH_LOD1_GML_DIR")
    out = PathConfig.OUTPUT / "compare_km"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for km in kilometres:
        bbox = _bbox_utm(km)
        logger.info("crop %dkm × %dkm  utm=%s", km, km, bbox)
        rows.extend(_run_trees(km, bbox, out))
        rows.extend(_run_terrain(km, bbox, out, dgm_dir))
        rows.extend(_run_city(km, bbox, out, lod1_dir))

    print()
    print(f"{'app':8} {'km':>3} {'writer':8} {'s':>7} {'MB':>6} {'proxy':>6} {'bldg':>5} {'pset':>5} {'faceset':>8}  note")
    for app, km, note, writer, seconds, path, ifc in rows:
        if path is None or not ifc.is_file():
            print(f"{app:8} {km:3} {writer:8}  FAILED  {note}")
            continue
        s = _stats(ifc)
        print(
            f"{app:8} {km:3} {writer:8} {seconds:7.2f} {s['mb']:6.2f} "
            f"{s['proxy']:6d} {s['bldg']:5d} {s['pset']:5d} {s['faceset']:8d}  {note}"
        )
    print("IFCs:", out)


if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(description="Compare generic vs rust on 1 km and 2 km crops")
    parser.add_argument("--km", type=int, nargs="+", choices=(1, 2), default=[1, 2])
    main(kilometres=tuple(parser.parse_args().km))
