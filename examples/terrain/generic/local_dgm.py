"""Resolve the local Hamburg DGM1 tile folder on Windows or WSL."""

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

_DGM_DIR_CANDIDATES = (
    Path(r"C:\_Lokale_Daten_ungesichert\___BIMFabrikHH_Datensaetze\dgm1_hh_2022-04-30"),
    Path("/mnt/c/_Lokale_Daten_ungesichert/___BIMFabrikHH_Datensaetze/dgm1_hh_2022-04-30"),
)


def resolve_dgm_dir() -> Path:
    """Return the DGM1 folder that exists on this machine.

    A hardcoded ``/mnt/c/...`` path becomes ``\\mnt\\c\\...`` under Windows
    Python and GDAL then reports the file as missing.
    """
    for path in _DGM_DIR_CANDIDATES:
        if path.is_dir():
            return path
    tried = "\n  ".join(str(p) for p in _DGM_DIR_CANDIDATES)
    raise FileNotFoundError(f"DGM1 folder not found. Tried:\n  {tried}")


def dgm_tile_paths() -> list[str]:
    folder = resolve_dgm_dir()
    files = [folder / name for name in _DGM_TILES]
    missing = [p for p in files if not p.is_file()]
    if missing:
        raise FileNotFoundError("DGM1 tiles missing:\n  " + "\n  ".join(str(p) for p in missing))
    return [str(p) for p in files]
