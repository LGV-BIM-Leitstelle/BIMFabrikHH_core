"""
Spatial Utilities Module

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
from typing import Optional

import numpy as np

logger = logging.getLogger("spatial_utils")


def is_building_in_bbox(vertices, bbox) -> bool:
    """
    Check if any vertex of the building is inside the bounding box.

    Args:
        vertices: List of (x, y, z) tuples or numpy array shape (N, 3)
        bbox: (minx, miny, maxx, maxy) tuple defining the bounding box

    Returns:
        bool: True if any vertex is inside the bounding box, False otherwise

    Example:
        >>> vertices = [(1, 2, 0), (3, 4, 0), (5, 6, 0)]
        >>> bbox = (0, 0, 4, 4)
        >>> is_building_in_bbox(vertices, bbox)
        True
    """
    arr = np.array(vertices)
    if arr.size == 0 or arr.ndim != 2 or arr.shape[1] < 2:
        return False  # No valid vertices to check
    inside = (arr[:, 0] >= bbox[0]) & (arr[:, 0] <= bbox[2]) & (arr[:, 1] >= bbox[1]) & (arr[:, 1] <= bbox[3])
    return np.any(inside)


def get_angle_from_2pts(p1: str, p2: str) -> Optional[float]:
    """
    Calculate the angle between two points relative to the X-axis.

    Args:
        p1 (str): First point as string "x,y".
        p2 (str): Second point as string "x,y".

    Returns:
        Optional[float]: Angle in degrees, or None if calculation fails.

    Raises:
        ValueError: If points are not in the expected format.

    Example:
        >>> get_angle_from_2pts("0,0", "1,1")
        45.0
        >>> get_angle_from_2pts("0,0", "1,0")
        0.0
    """
    # Splitting input points and converting to float
    try:
        x1, y1 = map(float, p1.split(","))
        x2, y2 = map(float, p2.split(","))
    except (AttributeError, ValueError) as e:
        logger.error(f"Error processing points: {e}")
        return None  # or set a default_data return value

    # Defining the origin and the point representing the rotation
    origin = np.array([x1, y1, 0], dtype=float)
    rotation_point = np.array([x2, y2, 0], dtype=float)

    # Computing the vector from the origin to the rotation point
    rotation_vector = rotation_point - origin

    # Checking for zero vector to avoid division by zero
    if np.linalg.norm(rotation_vector) == 0:
        logger.warning("The two points are the same, angle is undefined.")
        return None  # or set a default_data return value

    # Computing the angle between the X-axis and the rotation vector
    x_axis = np.array([1, 0, 0], dtype=float)
    cos_angle = np.dot(x_axis, rotation_vector) / (np.linalg.norm(x_axis) * np.linalg.norm(rotation_vector))

    # Clamping cos_angle to avoid invalid input for arccos
    cos_angle = np.clip(cos_angle, -1.0, 1.0)

    angle = np.arccos(cos_angle)

    # Converting the angle from radians to degrees
    angle_degrees = np.degrees(angle)

    # Adjusting the angle based on the Y-component to account for points above/below the origin
    if rotation_vector[1] < 0:
        angle_degrees = 360 - angle_degrees

    return angle_degrees


def parse_coordinates(coord_str: str) -> np.ndarray:
    """
    Convert a coordinate string 'x,y' to a NumPy array of floats.

    Args:
        coord_str (str): Coordinate string in format "x,y".

    Returns:
        np.ndarray: NumPy array with two float values [x, y].

    Raises:
        ValueError: If coord_str is not in the expected format.

    Example:
        >>> parse_coordinates("123.45,678.90")
        array([123.45, 678.9])
    """
    x_str, y_str = coord_str.split(",")
    return np.array([float(x_str), float(y_str)])
