import logging
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Union, overload

import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.sample import sample_gen

# Configure logging
logger = logging.getLogger(__name__)

# Hamburg DGM1 nodata is often ``float32`` min, not a water height.
_MAX_ABS_ELEVATION_M = 10_000.0


def elevation_ok(z: float, nodata: Optional[float] = None) -> bool:
    """True if ``z`` is a usable NHN height (not NaN / GeoTIFF nodata)."""
    try:
        value = float(z)
    except (TypeError, ValueError):
        return False
    if not np.isfinite(value) or abs(value) >= _MAX_ABS_ELEVATION_M:
        return False
    if nodata is not None and value == float(nodata):
        return False
    return True


def fill_nodata_from_nearest(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    nodata: Optional[float] = None,
) -> tuple[np.ndarray, int]:
    """Replace bad Z with the Z of the nearest valid XY sample.

    Same idea as rust ``terrain`` fill. If nothing is valid, bad Z becomes ``0``.
    """
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    out = np.asarray(zs, dtype=float).copy()
    ok = np.array([elevation_ok(z, nodata) for z in out], dtype=bool)
    if not np.any(ok):
        out[~ok] = 0.0
        return out, 0
    valid_i = np.flatnonzero(ok)
    filled = 0
    for i in np.flatnonzero(~ok):
        dx = xs[valid_i] - xs[i]
        dy = ys[valid_i] - ys[i]
        j = valid_i[int(np.argmin(dx * dx + dy * dy))]
        out[i] = out[j]
        filled += 1
    return out, filled


def _is_url(path: str) -> bool:
    """Check if a path is a URL."""
    return path.startswith(("http://", "https://"))


def _download_geotiff_to_memory(url: str, timeout: int = 60) -> Optional[BytesIO]:
    """Download a GeoTIFF file from URL into memory."""
    import requests

    try:
        logger.info(f"Downloading GeoTIFF from: {url}")
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        buffer = BytesIO(response.content)
        logger.info(f"Downloaded {len(response.content) / 1024 / 1024:.2f} MB to memory")
        return buffer
    except Exception as e:
        logger.error(f"Failed to download GeoTIFF: {e}")
        return None


def _extract_elevations_from_dataset(src, df: pd.DataFrame, easting_col: str, northing_col: str) -> np.ndarray:
    """Extract elevation values from an open rasterio dataset."""
    coords = list(zip(df[easting_col].values, df[northing_col].values))
    sample_values = list(sample_gen(src, coords, indexes=1))
    elevations = np.array(sample_values).flatten()
    xs = df[easting_col].to_numpy()
    ys = df[northing_col].to_numpy()
    elevations, filled = fill_nodata_from_nearest(xs, ys, elevations, src.nodata)

    if filled > 0:
        logger.warning("Rows without elevation data (filled from nearest valid): %s rows", filled)
    else:
        logger.info("All rows successfully assigned elevation values")

    return elevations.astype(float)


def extract_elevation_df_from_geotiff(
    df: pd.DataFrame, tif_path: str, easting_col: str, northing_col: str, elevation_col: str = "Elevation"
) -> pd.DataFrame:
    """
    Extract elevation values from a GeoTIFF file for locations in a DataFrame using vectorized operations.

    Supports both local file paths and HTTP/HTTPS URLs. URLs are downloaded and processed in-memory.

    Args:
        df (pd.DataFrame): DataFrame containing data with easting and northing columns.
        tif_path (str): Path to the GeoTIFF file OR URL to download from.
        easting_col (str): Name of the easting (X) column.
        northing_col (str): Name of the northing (Y) column.
        elevation_col (str): Name of the elevation column to write. Default is 'Elevation'.

    Returns:
        pd.DataFrame: DataFrame with updated elevation column.

    Raises:
        FileNotFoundError: If the GeoTIFF file cannot be found or downloaded.
        ValueError: If coordinate columns are missing or invalid.
        RuntimeError: If there are issues processing the elevation data.
    """
    # Input validation
    if df.empty:
        logger.warning("Empty DataFrame provided - no elevation data to extract")
        df[elevation_col] = 0.0
        return df

    # Check if path is a URL or local file
    is_url = _is_url(tif_path)

    if not is_url and not Path(tif_path).exists():
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")

    if easting_col not in df.columns:
        raise ValueError(
            f"Easting column '{easting_col}' not found in DataFrame. Available columns: {list(df.columns)}"
        )

    if northing_col not in df.columns:
        raise ValueError(
            f"Northing column '{northing_col}' not found in DataFrame. Available columns: {list(df.columns)}"
        )

    # Check for invalid coordinates
    invalid_coords = df[easting_col].isna() | df[northing_col].isna()
    if invalid_coords.any():
        invalid_count = invalid_coords.sum()
        logger.warning(f"Found {invalid_count} rows with invalid coordinates (NaN values)")

    try:
        if is_url:
            # Download and process in memory
            buffer = _download_geotiff_to_memory(tif_path)
            if buffer is None:
                raise FileNotFoundError(f"Failed to download GeoTIFF from: {tif_path}")

            with MemoryFile(buffer) as memfile:
                with memfile.open() as src:
                    df[elevation_col] = _extract_elevations_from_dataset(src, df, easting_col, northing_col)
        else:
            # Open local file
            with rasterio.open(tif_path) as src:
                df[elevation_col] = _extract_elevations_from_dataset(src, df, easting_col, northing_col)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error processing GeoTIFF file {tif_path}: {e}")

    return df


def extract_elevation_df_from_geotiff_optimized(
    df: pd.DataFrame, tif_path: str, easting_col: str, northing_col: str, elevation_col: str = "Elevation"
) -> pd.DataFrame:
    """
    Alternative optimized version using rasterio's sample() method with better error handling.
    """
    # Input validation
    if df.empty:
        logger.warning("Empty DataFrame provided - no elevation data to extract")
        df[elevation_col] = 0.0
        return df

    if not Path(tif_path).exists():
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")

    try:
        with rasterio.open(tif_path) as src:
            # Extract coordinates
            coords = list(zip(df[easting_col].values, df[northing_col].values))

            # Use rasterio's sample method for batch processing
            sample_values = list(src.sample(coords, indexes=1))

            # Convert to numpy array
            elevations = np.array(sample_values).flatten()
            elevations, filled = fill_nodata_from_nearest(
                df[easting_col].to_numpy(), df[northing_col].to_numpy(), elevations, src.nodata
            )
            df[elevation_col] = elevations.astype(float)

            if filled > 0:
                logger.warning("Rows without elevation data (filled from nearest valid): %s rows", filled)
            else:
                logger.info("All rows successfully assigned elevation values")

    except FileNotFoundError:
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")
    except Exception as e:
        raise RuntimeError(f"Error processing GeoTIFF file {tif_path}: {e}")

    return df


def get_elevation(src: rasterio.DatasetReader, x: Union[float, int], y: Union[float, int]) -> float:
    """
    Get elevation value for a single point from a GeoTIFF dataset.

    Args:
        src (rasterio.DatasetReader): Open rasterio dataset.
        x (float|int): Easting (X) coordinate.
        y (float|int): Northing (Y) coordinate.

    Returns:
        float: Elevation value at the given coordinate. Returns 0.0 if not found or on error.
    """
    try:
        # Validate input coordinates
        if pd.isna(x) or pd.isna(y):
            logger.warning(f"Invalid coordinates provided: x={x}, y={y}")
            return 0.0

        row_idx, col_idx = src.index(x, y)
        if 0 <= row_idx < src.height and 0 <= col_idx < src.width:
            z_value = src.read(1)[row_idx, col_idx]
            if z_value == src.nodata or pd.isna(z_value):
                return 0.0
            else:
                return float(z_value)
        else:
            logger.warning(f"Coordinate ({x}, {y}) is outside raster bounds")
            return 0.0
    except Exception as e:
        logger.error(f"Error processing coordinate ({x}, {y}): {e}")
        return 0.0


@overload
def extract_elevation_point_from_geotiff(easting: float, northing: float, tif_path: str) -> float: ...


@overload
def extract_elevation_point_from_geotiff(easting: List[float], northing: List[float], tif_path: str) -> List[float]: ...


def extract_elevation_point_from_geotiff(
    easting: Union[float, List[float]], northing: Union[float, List[float]], tif_path: str
) -> Union[float, List[float]]:
    """
    Extract elevation value(s) from a GeoTIFF file for given easting/northing coordinate(s).
    Optimized version using vectorized operations.

    Args:
        easting (float or list of float): Easting (X) coordinate(s).
        northing (float or list of float): Northing (Y) coordinate(s).
        tif_path (str): Path to the GeoTIFF file.

    Returns:
        float or list of float: Elevation value(s) at the given coordinate(s). Returns 0 if not found or on error.

    Raises:
        FileNotFoundError: If the GeoTIFF file cannot be found.
        ValueError: If coordinate lists have different lengths.
        RuntimeError: If there are issues processing the elevation data.
    """
    # Input validation
    if not Path(tif_path).exists():
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")

    try:
        with rasterio.open(tif_path) as src:
            if isinstance(easting, (list, tuple)) and isinstance(northing, (list, tuple)):
                # Validate input lists
                if len(easting) != len(northing):
                    raise ValueError(
                        f"Coordinate list lengths don't match: easting={len(easting)}, northing={len(northing)}"
                    )

                if len(easting) == 0:
                    logger.warning("Empty coordinate lists provided")
                    return []

                # Use vectorized sampling for multiple points
                coords = list(zip(easting, northing))
                sample_values = list(src.sample(coords, indexes=1))

                # Convert to numpy array and handle nodata
                elevations = np.array(sample_values).flatten()
                elevations, _ = fill_nodata_from_nearest(
                    np.asarray(easting, dtype=float),
                    np.asarray(northing, dtype=float),
                    elevations,
                    src.nodata,
                )

                return elevations.astype(float).tolist()
            else:
                # Single point - use the existing method
                return get_elevation(src, easting, northing)  # type: ignore
    except FileNotFoundError:
        raise FileNotFoundError(f"GeoTIFF file not found: {tif_path}")
    except ValueError:
        raise  # Re-raise ValueError for coordinate length mismatch
    except Exception as e:
        raise RuntimeError(f"Error processing GeoTIFF file {tif_path}: {e}")
