"""
Input record for the terrain app.

``TerrainMesh`` is the public input contract for
:meth:`BIMFabrikHH_core.apps.terrain.basic.TerrainBasicApp.build_ifc`.
It carries the triangulated mesh (vertices + faces) together with the
optional nullpunkt used for the project basepoint.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class TerrainMesh:
    """A triangulated terrain mesh ready for IFC export.

    Attributes:
        vertices: ``[[x, y, z], ...]`` in the project CRS (currently EPSG:25832).
        faces: ``[[i, j, k], ...]`` triangle indices into ``vertices``.
        nullpunkt: Optional ``(x, y)`` anchor for the IFC basepoint. When
            ``None`` the builder falls back to ``min(x), min(y)`` of the mesh.
    """

    vertices: List[List[float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    nullpunkt: Optional[Tuple[float, float]] = None

    def is_empty(self) -> bool:
        """True when the mesh has no geometry to write."""
        return not self.vertices or not self.faces
