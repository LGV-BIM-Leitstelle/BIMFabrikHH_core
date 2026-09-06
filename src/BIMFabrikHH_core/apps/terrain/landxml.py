"""LandXML 1.2 TIN export for terrain meshes.

Pure, IFC-agnostic writer: turns :class:`TerrainMesh` parts into a LandXML
``<Surface>`` per part (DGM plus each ALKIS Nutzung type), mirroring the IFC
objects produced by :class:`TerrainGenericApp`. Uses only the standard
library (``xml.etree.ElementTree``) so it adds no dependency.

Geometry stays in the project CRS (EPSG:25832, NHN heights). LandXML point
coordinates are written as ``northing easting elevation`` (Y X Z), the order
Civil 3D and most consumers expect. Point ids are 1-based and ``<F>`` faces
reference those ids.

All faces must be triangles; callers should triangulate n-gons first (the
terrain pipeline already produces triangle-only meshes).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Sequence, Tuple
from xml.etree import ElementTree as ET

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_landxml")

_LANDXML_NS = "http://www.landxml.org/schema/LandXML-1.2"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_SCHEMA_LOCATION = (
    "http://www.landxml.org/schema/LandXML-1.2 "
    "http://www.landxml.org/schema/LandXML-1.2/LandXML-1.2.xsd"
)


def _iter_triangles(faces: Sequence[Sequence[int]]) -> List[Tuple[int, int, int]]:
    """Fan-triangulate any non-triangle faces; pass triangles through."""
    tris: List[Tuple[int, int, int]] = []
    for face in faces:
        if len(face) == 3:
            tris.append((int(face[0]), int(face[1]), int(face[2])))
        elif len(face) > 3:
            a = int(face[0])
            for k in range(1, len(face) - 1):
                tris.append((a, int(face[k]), int(face[k + 1])))
    return tris


def _append_surface(surfaces_el: ET.Element, name: str, mesh: TerrainMesh) -> bool:
    """Append one ``<Surface>`` TIN. Return ``False`` when nothing was written."""
    if mesh.is_empty():
        return False
    tris = _iter_triangles(mesh.faces)
    if not tris:
        return False

    surface = ET.SubElement(surfaces_el, "Surface", {"name": name})
    definition = ET.SubElement(surface, "Definition", {"surfType": "TIN"})

    pnts = ET.SubElement(definition, "Pnts")
    for i, vertex in enumerate(mesh.vertices, start=1):
        x, y, z = float(vertex[0]), float(vertex[1]), float(vertex[2])
        point = ET.SubElement(pnts, "P", {"id": str(i)})
        # LandXML order: northing (Y) easting (X) elevation (Z).
        point.text = f"{y:.4f} {x:.4f} {z:.4f}"

    faces_el = ET.SubElement(definition, "Faces")
    for a, b, c in tris:
        # Point ids are 1-based.
        face = ET.SubElement(faces_el, "F")
        face.text = f"{a + 1} {b + 1} {c + 1}"

    logger.info("LandXML surface %s: %d points, %d triangles", name, len(mesh.vertices), len(tris))
    return True


def terrain_mesh_to_landxml(
    surfaces: Sequence[Tuple[str, TerrainMesh]],
    output_path: str | Path,
    *,
    epsg: int = 25832,
) -> Path:
    """Write ``surfaces`` as a LandXML 1.2 file with one TIN ``<Surface>`` each.

    Args:
        surfaces: ``(name, TerrainMesh)`` pairs. Empty meshes are skipped.
        output_path: Destination ``.xml`` path.
        epsg: EPSG code declared in ``<CoordinateSystem>`` (default 25832).

    Returns:
        The path written.
    """
    root = ET.Element(
        "LandXML",
        {
            "xmlns": _LANDXML_NS,
            "xmlns:xsi": _XSI_NS,
            "xsi:schemaLocation": _SCHEMA_LOCATION,
            "version": "1.2",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        },
    )
    units = ET.SubElement(root, "Units")
    ET.SubElement(
        units,
        "Metric",
        {
            "linearUnit": "meter",
            "areaUnit": "squareMeter",
            "volumeUnit": "cubicMeter",
            "temperatureUnit": "celsius",
            "pressureUnit": "milliBars",
        },
    )
    ET.SubElement(
        root,
        "CoordinateSystem",
        {"epsgCode": str(epsg), "name": f"EPSG:{epsg}"},
    )

    surfaces_el = ET.SubElement(root, "Surfaces")
    written = 0
    for name, mesh in surfaces:
        if _append_surface(surfaces_el, name, mesh):
            written += 1

    if written == 0:
        logger.warning("No non-empty surfaces; LandXML not written")

    dest = Path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(dest, encoding="utf-8", xml_declaration=True)
    logger.info("Saved LandXML with %d surface(s) → %s", written, dest)
    return dest


__all__ = ["terrain_mesh_to_landxml"]
