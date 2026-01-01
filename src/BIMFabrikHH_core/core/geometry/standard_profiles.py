"""
Standard Profile Objects
========================

This module provides a composable approach to creating standard profiles
using the existing primitive profile types (Rect, Circle, Polygon).
Follows the same pattern as city_furniture.py for consistency.
"""

from typing import List, Optional, Tuple

import ifcopenshell
from ifcfactory import BIMFactoryElement, Circle, Extrusion, Polygon, Rect, Style, Transform
from pydantic import BaseModel, Field


class StandardProfileConfig(BaseModel):
    """Configuration for standard profile dimensions and properties."""

    # Profile dimensions
    width: float = Field(default=1.0, description="Width of the profile")
    height: float = Field(default=1.0, description="Height of the profile")
    radius: float = Field(default=0.5, description="Radius for circular profiles")
    depth: float = Field(default=0.2, description="Depth for extrusion")

    # Profile type (only existing ones)
    profile_type: str = Field(default="rectangular", description="Type: rectangular, circular, polygon")

    # For polygon profiles
    polygon_points: List[Tuple[float, float]] = Field(default=[], description="Points for polygon profile")

    # Colors
    profile_color: Tuple[float, float, float] = Field(default=(0.5, 0.5, 0.5), description="Gray color for profile")


class StandardProfileBuilder:
    """Builder class for creating standard profile objects using existing primitive geometry."""

    def __init__(
        self,
        model: ifcopenshell.file,
        body_context: ifcopenshell.entity_instance,
        config: Optional[StandardProfileConfig] = None,
    ):
        """
        Initialize the standard profile builder.

        Args:
            model: The IFC model instance
            body_context: The body representation context
            config: Configuration for profile dimensions and properties
        """
        self.model = model
        self.body_context = body_context
        self.config = config or StandardProfileConfig()
        self.shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

    def create_rectangular_profile(self, name: str = "RectangularProfile"):
        """
        Create a rectangular profile using the existing Rect primitive.

        Args:
            name: Name for the profile element

        Returns:
            BIMFactoryElement: The rectangular profile
        """
        # Create rectangular profile using existing Rect primitive
        rect_profile = Rect(width=self.config.width, height=self.config.height)

        # Extrude it to create 3D geometry
        extruded = Extrusion(basis=rect_profile, depth=self.config.depth)

        # Style it
        styled = Style(item=extruded, rgb=self.config.profile_color)

        # Return as BIMFactoryElement
        return BIMFactoryElement(type="IfcBuildingElementProxy", children=[styled])

    def create_circular_profile(self, name: str = "CircularProfile"):
        """
        Create a circular profile using the existing Circle primitive.

        Args:
            name: Name for the profile element

        Returns:
            BIMFactoryElement: The circular profile
        """
        # Create circular profile using existing Circle primitive
        circle_profile = Circle(radius=self.config.radius)

        # Extrude it to create 3D geometry
        extruded = Extrusion(basis=circle_profile, depth=self.config.depth)

        # Style it
        styled = Style(item=extruded, rgb=self.config.profile_color)

        # Return as BIMFactoryElement
        return BIMFactoryElement(type="IfcBuildingElementProxy", children=[styled])

    def create_polygon_profile(self, name: str = "PolygonProfile"):
        """
        Create a polygon profile using the existing Polygon primitive.

        Args:
            name: Name for the profile element

        Returns:
            BIMFactoryElement: The polygon profile
        """
        # Use provided points or default triangle
        if not self.config.polygon_points:
            points = [(0, 0), (1, 0), (0.5, 1)]  # Default triangle
        else:
            points = self.config.polygon_points

        # Create polygon profile using existing Polygon primitive
        polygon_profile = Polygon(points=points)

        # Extrude it to create 3D geometry
        extruded = Extrusion(basis=polygon_profile, depth=self.config.depth)

        # Style it
        styled = Style(item=extruded, rgb=self.config.profile_color)

        # Return as BIMFactoryElement
        return BIMFactoryElement(type="IfcBuildingElementProxy", children=[styled])

    def create_standard_profile(self, profile_type: Optional[str] = None, name: str = "StandardProfile"):
        """
        Create a standard profile based on the specified type.

        Args:
            profile_type: Type of profile to create (rectangular, circular, polygon)
            name: Name for the profile element

        Returns:
            BIMFactoryElement: The created profile
        """
        profile_type = profile_type or self.config.profile_type

        if profile_type == "rectangular":
            return self.create_rectangular_profile(name)
        elif profile_type == "circular":
            return self.create_circular_profile(name)
        elif profile_type == "polygon":
            return self.create_polygon_profile(name)
        else:
            raise ValueError(f"Unknown profile type: {profile_type}. Available types: rectangular, circular, polygon")


def create_standard_profiles_example():
    """Example function demonstrating how to create standard profiles."""

    # Import here to avoid circular imports
    from BIMFabrikHH_core.core.model_creator.ifc_modelbuilder import IfcModelBuilder

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="StandardProfiles_Project",
        site_name="StandardProfiles_Site",
        building_name="StandardProfiles_Building",
        storey_name="StandardProfiles_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.body

    # Create standard profile builder
    config = StandardProfileConfig(width=2.0, height=1.0, radius=0.5, depth=0.3, profile_color=(0.7, 0.7, 0.7))
    builder = StandardProfileBuilder(model, body_context, config)

    # Create rectangular profile
    BIMFactoryElement(inst=storey, children=[builder.create_rectangular_profile("RectangularProfile_001")]).build(model)

    # Create circular profile
    BIMFactoryElement(
        inst=storey,
        children=[Transform(translation=(5, 0, 0), item=builder.create_circular_profile("CircularProfile_001"))],
    ).build(model)

    # Create polygon profile with custom points
    polygon_config = StandardProfileConfig(
        width=2.0,
        height=1.0,
        depth=0.3,
        profile_type="polygon",
        polygon_points=[(0, 0), (2, 0), (1, 1.5), (0, 0)],  # Triangle
        profile_color=(0.8, 0.6, 0.4),  # Brown color
    )
    polygon_builder = StandardProfileBuilder(model, body_context, polygon_config)

    BIMFactoryElement(
        inst=storey,
        children=[Transform(translation=(10, 0, 0), item=polygon_builder.create_polygon_profile("PolygonProfile_001"))],
    ).build(model)

    # Create profiles using the generic method
    profile_types = [
        ("rectangular", (15, 0, 0), (0.6, 0.8, 0.9)),  # Blue
        ("circular", (20, 0, 0), (0.9, 0.6, 0.8)),  # Pink
    ]

    for profile_type, position, color in profile_types:
        config = StandardProfileConfig(
            width=1.5, height=1.5, radius=0.75, depth=0.2, profile_type=profile_type, profile_color=color
        )
        profile_builder = StandardProfileBuilder(model, body_context, config)

        BIMFactoryElement(
            inst=storey,
            children=[
                Transform(
                    translation=position,
                    item=profile_builder.create_standard_profile(
                        profile_type, f"{profile_type.capitalize()}Profile_002"
                    ),
                )
            ],
        ).build(model)

    # Save the model
    output_file = "standard_profiles_example.ifc"
    model.write(output_file)

    print(f"Standard profiles IFC model created successfully: {output_file}")
    print("Created profiles:")
    print("  - Rectangular profile (gray)")
    print("  - Circular profile (gray)")
    print("  - Polygon profile (brown triangle)")
    print("  - Rectangular profile (blue)")
    print("  - Circular profile (pink)")


if __name__ == "__main__":
    create_standard_profiles_example()
