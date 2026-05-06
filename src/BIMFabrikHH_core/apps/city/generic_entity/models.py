"""DTOs and semantic mapping for typed CityGML → IFC export (generic_entity)."""

from __future__ import annotations

from typing import Dict, List, Literal, Tuple

from pydantic import BaseModel, Field

Point3 = Tuple[float, float, float]


class BoundaryPolygon(BaseModel):
    """One polygon on a semantic boundary surface (exterior ring + optional interior rings/voids)."""

    ring: List[Point3] = Field(min_length=3)
    interior_rings: List[List[Point3]] = Field(
        default_factory=list,
        description="Interior rings (courtyards / holes) parsed from gml:interior elements.",
    )
    surface_type: str = Field(description="Local name: RoofSurface, WallSurface, …")
    source_part_id: str | None = Field(default=None, description="BuildingPart gml:id if any")


# ---------------------------------------------------------------------------
# Semantic mapping: CityGML boundary surface type → IFC product class
# ---------------------------------------------------------------------------


IfcProductClass = Literal[
    "IfcRoof",
    "IfcWall",
    "IfcSlab",
    "IfcCovering",
    "IfcBuildingElementProxy",
]


class BoundarySurfaceMapping(BaseModel):
    """Maps one CityGML boundary surface tag (local name) to an IFC class."""

    surface_type: str = Field(description="XML local name, e.g. RoofSurface")
    ifc_type: IfcProductClass


DEFAULT_BOUNDARY_MAPPINGS: tuple[BoundarySurfaceMapping, ...] = (
    BoundarySurfaceMapping(surface_type="RoofSurface", ifc_type="IfcRoof"),
    BoundarySurfaceMapping(surface_type="WallSurface", ifc_type="IfcWall"),
    BoundarySurfaceMapping(surface_type="GroundSurface", ifc_type="IfcSlab"),
    BoundarySurfaceMapping(surface_type="OuterFloorSurface", ifc_type="IfcSlab"),
    BoundarySurfaceMapping(surface_type="OuterCeilingSurface", ifc_type="IfcCovering"),
    BoundarySurfaceMapping(surface_type="ClosureSurface", ifc_type="IfcBuildingElementProxy"),
)


def mapping_registry(
    extra: tuple[BoundarySurfaceMapping, ...] = (),
) -> Dict[str, IfcProductClass]:
    """Merge defaults with optional overrides / additions (last wins on duplicate kind)."""
    out: Dict[str, IfcProductClass] = {}
    for row in DEFAULT_BOUNDARY_MAPPINGS + extra:
        out[row.surface_type] = row.ifc_type
    return out
