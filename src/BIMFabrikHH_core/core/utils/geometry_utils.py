"""
Geometry Utilities Module

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
from typing import List, Tuple

import numpy

logger = logging.getLogger("geometry_utils")


def convert_to_indexed_geometry(
    faces: List[List[Tuple[float, float, float]]],
) -> Tuple[List[Tuple[float, float, float]], List[List[int]]]:
    """
    Convert face-vertex geometry to indexed format, with memoization for coordinate tuples.

    Args:
        faces: List of faces, where each face is a list of (x, y, z) coordinate tuples.

    Returns:
        Tuple containing:
        - vertices: List of unique (x, y, z) coordinate tuples
        - face_indices: List of faces, where each face is a list of vertex indices
    """
    if faces:
        try:
            # Flatten all points to a single array
            flat = numpy.asarray([p for face in faces for p in face], dtype=numpy.float64)
            flat = flat.reshape(-1, 3)

            uniq, first_index, inverse = numpy.unique(flat, axis=0, return_index=True, return_inverse=True)

            vertices = uniq.tolist()

            # rebuild per-face indices from inverse mapping
            face_indices = []
            idx_iter = iter(inverse.tolist())
            for face in faces:
                face_indices.append([next(idx_iter) for _ in face])

            return vertices, face_indices
        except Exception as e:
            raise RuntimeError(f"NumPy-based indexing failed: {e}")

    # Should never reach here if faces provided
    return [], []


def group3(seq) -> List[Tuple]:
    """
    Group a flat list into (x, y, z) tuples.

    Args:
        seq: Flat list of numbers (length should be multiple of 3)

    Returns:
        List of (x, y, z) tuples

    Example:
        >>> group3([1, 2, 3, 4, 5, 6])
        [(1, 2, 3), (4, 5, 6)]
    """
    return list(zip(seq[::3], seq[1::3], seq[2::3]))


def extract_polygon_points(polygon, ns) -> List[Tuple[float, float, float]]:
    """
    Vectorized extraction of points from a polygon element using numpy.
    Handles both exterior and interior rings (voids).

    Args:
        polygon: XML polygon element
        ns: Namespace dictionary for XML parsing

    Returns:
        List of (x, y, z) coordinate tuples for the exterior boundary only
        Note: Interior rings (voids) are currently ignored to maintain compatibility
    """
    face_points: List[Tuple[float, float, float]] = []

    # Extract exterior ring (main boundary)
    exterior_rings = polygon.xpath(".//gml:exterior//gml:posList", namespaces=ns)
    if exterior_rings:
        txt = exterior_rings[0].text.strip()
        try:
            arr = numpy.fromstring(txt, sep=" ", dtype=numpy.float64).reshape(-1, 3)
            face_points = [tuple(row) for row in arr]
        except ValueError:
            pass

    return face_points


def extract_polygon_with_voids(
    polygon, ns
) -> Tuple[List[Tuple[float, float, float]], List[List[Tuple[float, float, float]]]]:
    """
    Extract polygon with voids from a polygon element.

    Args:
        polygon: XML polygon element
        ns: Namespace dictionary for XML parsing

    Returns:
        Tuple containing:
        - exterior_points: List of (x, y, z) coordinate tuples for the exterior boundary
        - interior_points: List of lists, where each inner list contains (x, y, z) coordinate tuples for interior rings (voids)
    """
    exterior_points: List[Tuple[float, float, float]] = []
    interior_points: List[List[Tuple[float, float, float]]] = []

    # Extract exterior ring (main boundary)
    exterior_rings = polygon.xpath(".//gml:exterior//gml:posList", namespaces=ns)
    if exterior_rings:
        txt = exterior_rings[0].text.strip()
        try:
            arr = numpy.fromstring(txt, sep=" ", dtype=numpy.float64).reshape(-1, 3)
            exterior_points = [tuple(row) for row in arr]
        except ValueError:
            pass

    # Extract interior rings (voids)
    interior_rings = polygon.xpath(".//gml:interior//gml:posList", namespaces=ns)
    for interior_ring in interior_rings:
        txt = interior_ring.text.strip()
        try:
            arr = numpy.fromstring(txt, sep=" ", dtype=numpy.float64).reshape(-1, 3)
            if arr.size:
                interior_points.append([tuple(row) for row in arr])
        except ValueError:
            pass

    return exterior_points, interior_points


def convert_faces_with_voids_to_ifc_format(
    faces_with_voids: List[Tuple[List[Tuple[float, float, float]], List[List[Tuple[float, float, float]]]]],
) -> Tuple[List[Tuple[float, float, float]], List]:
    """
    Convert faces with voids to IFC format using IfcIndexedPolygonalFaceWithVoids.

    Args:
        faces_with_voids: List of tuples, where each tuple contains:
            - exterior_points: List of (x, y, z) coordinate tuples for the exterior boundary
            - interior_points: List of lists, where each inner list contains (x, y, z) coordinate tuples for interior rings (voids)

    Returns:
        Tuple containing:
        - vertices: List of unique (x, y, z) coordinate tuples
        - face_structures: List of face structures that can be used to create IfcIndexedPolygonalFaceWithVoids
    """
    # Flatten points for vectorised deduplication
    flat_pts = []
    rings_len = []  # lengths to reconstruct indices
    for ext, inners in faces_with_voids:
        flat_pts.extend(ext)
        rings_len.append(len(ext))
        for ring in inners:
            flat_pts.extend(ring)
            rings_len.append(len(ring))

    arr = numpy.asarray(flat_pts, dtype=numpy.float64).reshape(-1, 3)
    uniq, first_idx, inv = numpy.unique(arr, axis=0, return_index=True, return_inverse=True)

    vertices = uniq.tolist()

    # rebuild face structures
    face_structures: List = []
    cursor = 0
    for ext, inners in faces_with_voids:
        ext_len = len(ext)
        ext_indices = (inv[cursor : cursor + ext_len] + 1).tolist()
        cursor += ext_len
        inner_idx_list = []
        for ring in inners:
            L = len(ring)
            inner_idx_list.append((inv[cursor : cursor + L] + 1).tolist())
            cursor += L
        face_structures.append(
            {
                "type": "IfcIndexedPolygonalFaceWithVoids" if inner_idx_list else "IfcIndexedPolygonalFace",
                "coord_index": ext_indices,
                "inner_coord_indices": inner_idx_list,
            }
        )

    return vertices, face_structures
