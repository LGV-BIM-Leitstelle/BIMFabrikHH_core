"""Sample ground elevation from one or more DGM GeoTIFF tiles.

App-agnostic: trees, streets, and terrain all call
:func:`sample_elevations_for_points`. Local paths and ``http(s)://`` URLs
are accepted. Hamburg DGM1 nodata (GDAL sentinel and the ``0.0`` fill) is
treated as missing.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional, Union

import numpy as np
import rasterio
from rasterio.io import MemoryFile

from BIMFabrikHH_core.config.logging_config import get_logger

logger = get_logger("extract_elevation")

# GDAL float32 nodata and the 0.0 fill used in some Hamburg DGM1 holes.
_NODATA_SENTINEL = -1e20
_ZERO_FILL = 0.0


def is_url(path: Union[str, Path]) -> bool:
    """Return ``True`` if ``path`` is an HTTP(S) URL."""
    return str(path).startswith(("http://", "https://"))


def download_to_memory(url: str, timeout: int = 120) -> Optional[BytesIO]:
    """Download a file from ``url`` into memory.

    Returns a :class:`BytesIO` buffer on success, ``None`` on failure.
    ``requests`` is imported lazily so local-only callers skip it.
    """
    import requests

    try:
        logger.info("Downloading from: %s", url)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        buffer = BytesIO(response.content)
        logger.info("Downloaded %.2f MB to memory", len(response.content) / 1024 / 1024)
        return buffer
    except Exception as exc:
        logger.error("Failed to download: %s", exc)
        return None


def invalid_z(values: np.ndarray, nodata: Optional[float] = None) -> np.ndarray:
    """True where ``values`` are missing, GDAL nodata, or the 0.0 DGM fill."""
    v = np.asarray(values, dtype=float)
    invalid = ~np.isfinite(v)
    invalid |= v <= _NODATA_SENTINEL
    if nodata is not None and np.isfinite(float(nodata)):
        invalid |= np.isclose(v, float(nodata))
    invalid |= v == _ZERO_FILL
    return invalid


class _MemoryFileContext:
    """Adapter that opens a rasterio ``MemoryFile`` as a dataset."""

    def __init__(self, memfile: MemoryFile) -> None:
        self._memfile = memfile
        self._src = None

    def __enter__(self):
        self._src = self._memfile.__enter__().open()
        return self._src

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._src is not None:
                self._src.close()
        finally:
            return self._memfile.__exit__(exc_type, exc, tb)


def open_geotiff(path: Union[str, Path]):
    """Open a GeoTIFF from a local path or URL.

    Returns a context manager yielding an open rasterio dataset.
    URL fetches are buffered entirely in memory via ``MemoryFile``.
    """
    if is_url(path):
        buffer = download_to_memory(str(path))
        if buffer is None:
            raise RuntimeError(f"Failed to download GeoTIFF: {path}")
        return _MemoryFileContext(MemoryFile(buffer))
    return rasterio.open(str(path))


def sample_elevations_from_raster(src, x_coords: np.ndarray, y_coords: np.ndarray) -> np.ndarray:
    """Sample elevation values from an open rasterio dataset.

    Points outside the raster, GDAL nodata, and the ``0.0`` DGM fill return ``NaN``.
    """
    coords = list(zip(x_coords, y_coords))
    samples = list(src.sample(coords))
    values = np.array([s[0] if len(s) > 0 else np.nan for s in samples], dtype=float)
    values[invalid_z(values, getattr(src, "nodata", None))] = np.nan
    return values


def sample_elevations_for_points(
    points_xy: np.ndarray,
    tif_files: Iterable[Union[str, Path]],
    *,
    folder_path: Optional[Union[str, Path]] = None,
    default_elevation: float = 0.0,
) -> np.ndarray:
    """Sample ground elevation for ``points_xy`` (``(N, 2)`` EPSG:25832) from DGM tiles.

    Walks every tile; the first tile that yields a valid (non-NaN, non-nodata)
    value wins. Points not covered by any tile fall back to ``default_elevation``.
    """
    n = len(points_xy)
    if n == 0:
        return np.empty(0, dtype=float)

    elevations = np.full(n, np.nan, dtype=float)
    x = points_xy[:, 0]
    y = points_xy[:, 1]

    for file in tif_files:
        if not np.any(np.isnan(elevations)):
            break
        if folder_path is not None:
            path: Union[str, Path] = f"{folder_path}/{file}" if is_url(folder_path) else Path(folder_path) / file
        else:
            path = file
        try:
            with open_geotiff(path) as src:
                bounds = src.bounds
                todo = np.isnan(elevations)
                in_raster = (
                    todo
                    & (x >= bounds.left)
                    & (x <= bounds.right)
                    & (y >= bounds.bottom)
                    & (y <= bounds.top)
                )
                if not np.any(in_raster):
                    continue
                sampled = sample_elevations_from_raster(src, x[in_raster], y[in_raster])
                idx = np.where(in_raster)[0]
                valid = ~np.isnan(sampled)
                elevations[idx[valid]] = sampled[valid]
                logger.info("Sampled %d/%d points from %s", int(np.sum(valid)), n, path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Error sampling elevations from %s: %s", path, exc)
            continue

    missing = int(np.sum(np.isnan(elevations)))
    if missing:
        logger.warning("%d/%d points had no DGM coverage; set to %.3f", missing, n, default_elevation)
    return np.where(np.isnan(elevations), default_elevation, elevations)
