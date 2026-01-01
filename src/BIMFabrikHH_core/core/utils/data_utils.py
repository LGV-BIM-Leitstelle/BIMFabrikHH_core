"""
Data Utilities Module

Copyright (C) 2025 Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung
BIM-Leitstelle, Ahmed Salem <ahmed.salem@gv.hamburg.de>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

import logging

import numpy as np

logger = logging.getLogger("data_utils")


def preprocess_elevation_data(elevation_data: np.ndarray) -> np.ndarray:
    """
    Fast preprocessing of elevation data with minimal operations.

    Args:
        elevation_data (np.ndarray): Raw elevation data from rasterio.

    Returns:
        np.ndarray: Processed elevation data ready for mesh generation.

    Example:
        >>> data = np.array([[1, 2], [3, 4]], dtype=np.float32)
        >>> processed = preprocess_elevation_data(data)
        >>> processed.shape
        (2, 2)
    """
    # Convert to float32 for memory efficiency
    data = elevation_data.astype(np.float32)

    # Replace invalid values (NaN, inf) with 0
    data[~np.isfinite(data)] = 0

    # Handle empty or constant value cases
    if data.size == 0 or np.all(data == data.flat[0]):
        return np.zeros_like(data, dtype=np.float32)

    # Simple min-max normalization to reasonable elevation range
    if data.max() != data.min():
        data = (data - data.min()) * (10.0 / (data.max() - data.min()))

    return data
