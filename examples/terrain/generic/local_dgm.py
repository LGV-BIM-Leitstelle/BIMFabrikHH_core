"""DGM1 tiles for the generic terrain examples.

Looks in ``examples/assets/dgm1_hh_2022-04-30`` first. Missing tiles are
taken from ``BIMFABRIKHH_DGM_TIF_DIR`` or the local
``___BIMFabrikHH_Datensaetze/dgm1_hh_2022-04-30`` archive (Windows + WSL)
and copied into assets.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from pyproj import Transformer

from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams

# WGS84 crop: Innenstadt / Binnenalster–Außenalster (same as terrain README OAF example).
# Innenstadt / Alster, 950 m × 950 m (~0.90 km²) so the API 1 km² cap accepts it.
EXAMPLE_BBOX = BoundingBoxParams(min_x=9.9769, min_y=53.5478, max_x=9.991435, max_y=53.55622)

_TILE_NAME = "dgm1_32_{easting}_{northing}_1_hh_2022.tif"
# Same default as ``extract_mesh_adaptive(..., buffer_meters=100)``.
_BBOX_BUFFER_M = 100.0
_ASSETS = Path(__file__).resolve().parents[2] / "assets" / "dgm1_hh_2022-04-30"

_ARCHIVE_WIN = r"C:\_Lokale_Daten_ungesichert\___BIMFabrikHH_Datensaetze\dgm1_hh_2022-04-30"
_ARCHIVE_MNT = "/mnt/c/_Lokale_Daten_ungesichert/___BIMFabrikHH_Datensaetze/dgm1_hh_2022-04-30"

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
        return Path(f"/mnt/{win.group(1).lower()}/{win.group(2) or ''}")
    return None


def _path_variants(raw: str) -> list[Path]:
    seen: list[Path] = []
    for candidate in (_as_windows(raw), _as_mnt(raw), Path(raw).expanduser()):
        if candidate is None or candidate in seen:
            continue
        seen.append(candidate)
    return seen


def _search_dirs() -> list[Path]:
    dirs: list[Path] = []
    raw = os.environ.get("BIMFABRIKHH_DGM_TIF_DIR", "").strip()
    if raw:
        dirs.extend(_path_variants(raw))
    dirs.extend(_path_variants(_ARCHIVE_WIN))
    dirs.extend(_path_variants(_ARCHIVE_MNT))
    existing = [p for p in dirs if p.is_dir()]
    extra: list[Path] = []
    for folder in existing:
        nested = folder / "dgm1_hh_2022"
        if nested.is_dir() and nested not in existing and nested not in extra:
            extra.append(nested)
    return existing + extra


def _tile_names(bbox: BoundingBoxParams) -> list[str]:
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:25832", always_xy=True)
    e0, n0 = to_utm.transform(bbox.min_x, bbox.min_y)
    e1, n1 = to_utm.transform(bbox.max_x, bbox.max_y)
    min_e, max_e = min(e0, e1) - _BBOX_BUFFER_M, max(e0, e1) + _BBOX_BUFFER_M
    min_n, max_n = min(n0, n1) - _BBOX_BUFFER_M, max(n0, n1) + _BBOX_BUFFER_M
    east0 = int(min_e // 1000)
    east1 = int((max_e - 1e-9) // 1000)
    north0 = int(min_n // 1000)
    north1 = int((max_n - 1e-9) // 1000)
    names: list[str] = []
    for easting in range(east0, east1 + 1):
        for northing_km in range(north0, north1 + 1):
            names.append(_TILE_NAME.format(easting=easting, northing=(northing_km % 1000) * 10))
    return names


def _find_tile(name: str, search_dirs: list[Path]) -> Path | None:
    easting = name.split("_")[2]
    relative = (
        Path(name),
        Path("dgm1_hh_2022") / f"s32_{easting}" / name,
        Path(f"s32_{easting}") / name,
    )
    for folder in search_dirs:
        for rel in relative:
            path = folder / rel
            if path.is_file():
                return path
    return None


def resolve_dgm_dir() -> Path:
    """Return ``examples/assets/dgm1_hh_2022-04-30``, creating it if needed."""
    _ASSETS.mkdir(parents=True, exist_ok=True)
    return _ASSETS


def dgm_tile_paths(bbox: BoundingBoxParams | None = None) -> list[str]:
    """Return GeoTIFF paths covering ``bbox`` (defaults to ``EXAMPLE_BBOX``)."""
    crop = bbox or EXAMPLE_BBOX
    assets = resolve_dgm_dir()
    search = _search_dirs()
    files: list[Path] = []
    missing: list[str] = []
    for name in _tile_names(crop):
        dest = assets / name
        if dest.is_file():
            files.append(dest)
            continue
        source = _find_tile(name, search)
        if source is None:
            missing.append(name)
            continue
        shutil.copy2(source, dest)
        files.append(dest)
    if missing:
        raise FileNotFoundError(
            "DGM1 tiles missing for bbox "
            f"({crop.min_x}, {crop.min_y}–{crop.max_x}, {crop.max_y}):\n  "
            + "\n  ".join(missing)
            + "\nSet BIMFABRIKHH_DGM_TIF_DIR or place the tiles in "
            + str(assets)
        )
    return [str(p) for p in files]
