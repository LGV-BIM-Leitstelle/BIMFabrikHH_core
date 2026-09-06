"""DGM1 tiles shipped under ``examples/assets`` (path relative to this file)."""

from __future__ import annotations

from pathlib import Path

_DGM_TILES = [
    "dgm1_32_564_9330_1_hh_2022.tif",
    "dgm1_32_564_9340_1_hh_2022.tif",
    "dgm1_32_565_9330_1_hh_2022.tif",
    "dgm1_32_565_9340_1_hh_2022.tif",
    "dgm1_32_566_9330_1_hh_2022.tif",
    "dgm1_32_566_9340_1_hh_2022.tif",
]

# examples/terrain/generic/this file → examples/assets/dgm1_hh_2022-04-30
_DGM_DIR = Path(__file__).resolve().parents[2] / "assets" / "dgm1_hh_2022-04-30"


def resolve_dgm_dir() -> Path:
    """Return ``examples/assets/dgm1_hh_2022-04-30``."""
    if not _DGM_DIR.is_dir():
        raise FileNotFoundError(f"DGM1 folder not found: {_DGM_DIR}")
    return _DGM_DIR


def dgm_tile_paths() -> list[str]:
    folder = resolve_dgm_dir()
    files = [folder / name for name in _DGM_TILES]
    missing = [p for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("DGM1 tiles missing:\n  " + "\n  ".join(str(p) for p in missing))
    return [str(p) for p in files]
