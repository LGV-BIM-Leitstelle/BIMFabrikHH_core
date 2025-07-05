from typing import List, Union, overload

import pandas as pd
import rasterio

def extract_elevation_df_from_geotiff(
    df: pd.DataFrame, tif_path: str, easting_col: str, northing_col: str, elevation_col: str = "Elevation"
) -> pd.DataFrame:
    """
    Extract elevation values from a GeoTIFF file for locations in a DataFrame and update the DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing data with easting and northing columns.
        tif_path (str): Path to the GeoTIFF file.
        easting_col (str): Name of the easting (X) column.
        northing_col (str): Name of the northing (Y) column.
        elevation_col (str): Name of the elevation column to write. Default is 'Elevation'.

    Returns:
        pd.DataFrame: DataFrame with updated elevation column.
    """
    trees_without_elevation = []
    elevations = []

    try:
        with rasterio.open(tif_path) as src:
            for idx, row in df.iterrows():
                longitude = row[easting_col]
                latitude = row[northing_col]

                try:
                    row_idx, col_idx = src.index(longitude, latitude)
                    if 0 <= row_idx < src.height and 0 <= col_idx < src.width:
                        z_value = src.read(1)[row_idx, col_idx]
                        if z_value == src.nodata or pd.isna(z_value):
                            elevations.append(0)
                            trees_without_elevation.append(idx)
                        else:
                            elevations.append(float(z_value))
                    else:
                        elevations.append(0)
                        trees_without_elevation.append(idx)
                except Exception as e:
                    print(f"Error processing row at index {idx}: {e}")
                    elevations.append(0)
                    trees_without_elevation.append(idx)
    except Exception as e:
        print(f"Error opening GeoTIFF file {tif_path}: {e}")
        elevations = [0] * len(df)
        trees_without_elevation = list(df.index)

    df[elevation_col] = elevations

    if trees_without_elevation:
        print(f"Rows without elevation data (set to 0): {len(trees_without_elevation)} rows")
        print(f"Row indices: {trees_without_elevation}")
    else:
        print("All rows successfully assigned elevation values")
        print(df[elevation_col])

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
        row_idx, col_idx = src.index(x, y)
        if 0 <= row_idx < src.height and 0 <= col_idx < src.width:
            z_value = src.read(1)[row_idx, col_idx]
            if z_value == src.nodata or pd.isna(z_value):
                return 0.0
            else:
                return float(z_value)
        else:
            return 0.0
    except Exception as e:
        print(f"Error processing coordinate ({x}, {y}): {e}")
        return 0.0


@overload
def extract_elevation_point_from_geotiff(
    easting: float, northing: float, tif_path: str
) -> float:
    ...


@overload
def extract_elevation_point_from_geotiff(
    easting: List[float], northing: List[float], tif_path: str
) -> List[float]:
    ...


def extract_elevation_point_from_geotiff(
    easting: Union[float, List[float]], northing: Union[float, List[float]], tif_path: str
) -> Union[float, List[float]]:
    """
    Extract elevation value(s) from a GeoTIFF file for given easting/northing coordinate(s).

    Args:
        easting (float or list of float): Easting (X) coordinate(s).
        northing (float or list of float): Northing (Y) coordinate(s).
        tif_path (str): Path to the GeoTIFF file.

    Returns:
        float or list of float: Elevation value(s) at the given coordinate(s). Returns 0 if not found or on error.
    """
    try:
        with rasterio.open(tif_path) as src:
            if isinstance(easting, (list, tuple)) and isinstance(northing, (list, tuple)):
                return [get_elevation(src, x, y) for x, y in zip(easting, northing)]
            else:
                return get_elevation(src, easting, northing)  # type: ignore
    except Exception as e:
        print(f"Error opening GeoTIFF file {tif_path}: {e}")
        if isinstance(easting, (list, tuple)) and isinstance(northing, (list, tuple)):
            return [0.0] * min(len(easting), len(northing))
        else:
            return 0.0
