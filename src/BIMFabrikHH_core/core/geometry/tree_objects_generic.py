"""
Tree Objects Generic Module
===========================

This module provides generic tree object creation functionality
that can be used across different tree applications.
"""

from typing import List, Optional, Tuple

from ifcfactory import BIMFactoryElement, NgonCylinder, Sphere, Style, Transform


def create_tree_element(
    position: Tuple[float, float, float],
    crown_radius: float,
    trunk_radius: float,
    trunk_height: float,
    crown_detail: int = 1,
    trunk_segments: int = 8,
    psets: Optional[List] = None,
    trunk_color: Tuple[float, float, float] = (0.44, 0.27, 0.18),
    crown_color: Tuple[float, float, float] = (0.13, 0.50, 0.18),
    name: str = "Baum",
    name_prefix: str = "",
    trunk_layer: str = "_BIM_SBK_Stamm",
    crown_layer: str = "_BIM_SBK_Krone",
) -> BIMFactoryElement:
    """
    Create a tree BIMFactoryElement with the given parameters.

    This function follows the stadtmobiliar pattern where:
    - Geometry is created at origin (0,0,0)
    - Positioning is handled via ObjectPlacement (Transform wrapper)
    - Coordinates are stored in ObjectPlacement.RelativePlacement.Location
    - Geometry coordinates remain local to the object

    Args:
        position: 3D position of the tree (x, y, z) - will be stored in ObjectPlacement
        crown_radius: Radius of the tree crown
        trunk_radius: Radius of the tree trunk
        trunk_height: Height of the tree trunk
        crown_detail: Detail level for crown sphere
        trunk_segments: Number of segments for trunk cylinder
        psets: Optional list of property sets
        trunk_color: RGB tuple for trunk color (default: brown (0.44, 0.27, 0.18))
        crown_color: RGB tuple for crown color (default: green (0.13, 0.50, 0.18))
        name: Name of the tree object
        name_prefix: Prefix to add to the tree name (e.g., "SBK_Mengestrasse_")
        trunk_layer: CAD layer name for trunk geometry (default: "_BIM_SBK_Stamm")
        crown_layer: CAD layer name for crown geometry (default: "_BIM_SBK_Krone")

    Returns:
        BIMFactoryElement representing the tree as a single object with proper ObjectPlacement
    """
    # Create tree geometry at origin (0,0,0) - following stadtmobiliar pattern
    components = []

    # Create trunk component at origin
    trunk_component = Style(
        item=NgonCylinder(radius=trunk_radius, height=trunk_height, segments=trunk_segments),
        rgb=trunk_color,
        transparency=0.0,
        cad_layer=trunk_layer,
    )
    components.append(trunk_component)

    # Create crown component positioned at the top of the trunk (still at origin)
    crown_component = Style(
        item=Transform(
            translation=(0.0, 0.0, trunk_height),  # Local translation within the tree object
            item=Sphere(radius=crown_radius, detail=crown_detail),
        ),
        rgb=crown_color,
        transparency=0.0,
        cad_layer=crown_layer,
    )
    components.append(crown_component)

    # Create the tree object with geometry at origin
    # Apply name prefix if provided
    final_name = f"{name_prefix}{name}" if name_prefix else name

    tree_object = BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=final_name,
        qsets=False,
        children=components,
        psets=psets or [],
    )

    # Apply positioning via Transform wrapper (this creates proper ObjectPlacement)
    # This follows the same pattern as stadtmobiliar where positioning is handled externally
    positioned_tree = Transform(translation=(position[0], position[1], position[2]), item=tree_object)

    return positioned_tree
