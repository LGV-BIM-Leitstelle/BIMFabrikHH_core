"""
City Furniture Objects
======================

This module contains city furniture objects created using primitive geometry.
Currently, supports bus stations with different levels of detail (LOD),
oval objects, and sweep objects for generic city furniture creation.
"""

from typing import Optional, Tuple

import ifcopenshell
import ifcopenshell.util.shape_builder
from ifcfactory import BIMFactoryElement, Box, EllipticalCylinder, Primitive, RepresentationItem, Style, Transform
from pydantic import BaseModel, Field

from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates


class SweptDiskSolid(Primitive, RepresentationItem):
    """Custom primitive for creating swept disk solids."""

    length: float
    height: float
    radius: float
    centered: bool = True

    def build(self, model: ifcopenshell.file) -> ifcopenshell.entity_instance:
        """
        Build a swept disk solid.

        Args:
            model: The IFC model instance

        Returns:
            ifcopenshell.entity_instance: The created swept disk solid
        """
        shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

        # Create the profile curve
        if self.centered:
            # Create the polyline centered at (0,0) - for "mittig"
            half_length = self.length / 2
            profile_curve = shape_builder.polyline(
                [
                    (-half_length, 0.0, 0.0),  # Start at the left base
                    (-half_length, 0.0, self.height),  # Height at left
                    (half_length, 0.0, self.height),  # Height at right
                    (half_length, 0.0, 0.0),  # End at the right base
                ]
            )
        else:
            # Create the polyline starting at (0,0) - for "endpunkt"
            profile_curve = shape_builder.polyline(
                [
                    (0.0, 0.0, 0.0),  # Start at the base (not centered)
                    (0.0, 0.0, self.height),  # Height of the object
                    (self.length, 0.0, self.height),  # Extend along the X-axis
                    (self.length, 0.0, 0.0),  # End at the base
                ]
            )

        # Create the swept disk solid
        return shape_builder.create_swept_disk_solid(profile_curve, self.radius)


class LShapedSweptDiskSolid(Primitive, RepresentationItem):
    """Custom primitive for creating L-shaped swept disk solids for objekt_ausleger (generic L-shaped objects)."""

    length: float
    height: float
    radius: float

    def build(self, model: ifcopenshell.file) -> ifcopenshell.entity_instance:
        """
        Build an L-shaped swept disk solid.

        Args:
            model: The IFC model instance

        Returns:
            ifcopenshell.entity_instance: The created L-shaped swept disk solid
        """
        shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

        # Create L-shaped polyline profile
        # Vertical part: from (0,0,0) to (0,0,height)
        # Horizontal part: from (0,0,height) to (length,0,height)
        l_profile = shape_builder.polyline(
            [
                (0.0, 0.0, 0.0),  # Start at base
                (0.0, 0.0, self.height),  # Go up vertically
                (self.length, 0.0, self.height),  # Go right horizontally
            ]
        )

        # Create the swept disk solid
        return shape_builder.create_swept_disk_solid(l_profile, self.radius)


class LShapedCurvedSweptDiskSolid(Primitive, RepresentationItem):
    """Custom primitive for creating L-shaped swept disk solids with fillet corner."""

    length: float
    height: float
    radius: float

    def build(self, model: ifcopenshell.file) -> ifcopenshell.entity_instance:
        """
        Build an L-shaped swept disk solid with fillet corner.

        Args:
            model: The IFC model instance

        Returns:
            ifcopenshell.entity_instance: The created L-shaped fillet swept disk solid
        """
        shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

        # Create L-shaped polyline with 5 points like the example pattern
        # Use a smaller radius for the fillet (10% of smaller dimension)
        fillet_radius = min(self.length, self.height) * 0.4

        l_profile = shape_builder.polyline(
            [
                (0.0, 0.0, 0.0),  # Point 1: Start at base
                (0.0, 0.0, self.height - fillet_radius),  # Point 2: Go up before fillet
                (fillet_radius, 0.0, self.height),  # Point 3: Fillet curve point ← ARC POINT
                (self.length - fillet_radius, 0.0, self.height),  # Point 4: After fillet
                (self.length, 0.0, self.height),  # Point 5: End horizontally
            ],
            arc_points=[2],
        )  # Make point 3 (index 2) the arc point for fillet

        # Create the swept disk solid
        return shape_builder.create_swept_disk_solid(l_profile, self.radius)


class BusStationConfig(BaseModel):
    """Configuration for bus station dimensions and colors."""

    # Dimensions
    width: float = Field(default=4.0, description="Width of the bus station")
    depth: float = Field(default=1.61, description="Depth of the bus station")
    height: float = Field(default=2.45, description="Height of the bus station")
    frame_width: float = Field(default=0.1, description="Width of frame columns")
    frame_depth: float = Field(default=0.05, description="Depth of frame columns")
    thickness: float = Field(default=0.1, description="Thickness of panels")
    seat_width: float = Field(default=2.0, description="Width of seating area")
    seat_depth: float = Field(default=0.4, description="Depth of seating area")
    seat_height: float = Field(default=0.5, description="Height of seating area")

    # Colors (RGB tuples)
    lod2_color: Tuple[float, float, float] = Field(default=(1.0, 0.25, 0.0), description="Orange color for LOD2")
    roof_color: Tuple[float, float, float] = Field(default=(0.25, 0.25, 0.25), description="Dark gray for roof")
    seat_color: Tuple[float, float, float] = Field(default=(0.5, 0.5, 0.5), description="Gray for seats")
    glass_color: Tuple[float, float, float] = Field(default=(0.8, 0.9, 0.88), description="Light blue for glass")
    columns_color: Tuple[float, float, float] = Field(default=(0.5, 0.5, 0.5), description="Gray for columns")


class OvalConfig(BaseModel):
    """Configuration for oval objects."""

    # Dimensions
    width: float = Field(default=1.0, description="Width of the oval")
    depth: float = Field(default=0.5, description="Depth of the oval")
    height: float = Field(default=1.0, description="Height of the oval")

    # Colors (RGB tuples)
    color: Tuple[float, float, float] = Field(default=(0.5, 0.5, 0.5), description="Color for the oval")


class SweepConfig(BaseModel):
    """Configuration for sweep objects."""

    # Dimensions
    length: float = Field(default=1.0, description="Length of the sweep")
    depth: float = Field(default=0.1, description="Depth of the sweep")
    height: float = Field(default=1.0, description="Height of the sweep")

    # Colors (RGB tuples)
    color: Tuple[float, float, float] = Field(default=(0.5, 0.5, 0.5), description="Color for the sweep")


class BusStationBuilder:
    """Builder class for creating bus station objects using primitive geometry."""

    def __init__(
        self,
        model: ifcopenshell.file,
        body_context: ifcopenshell.entity_instance,
        config: Optional[BusStationConfig] = None,
    ):
        """
        Initialize the bus station builder.

        Args:
            model: The IFC model instance
            body_context: The body representation context
            config: Configuration for bus station dimensions and colors
        """
        self.model = model
        self.body_context = body_context
        self.config = config or BusStationConfig()
        self.shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

    def create_bus_station_lod1(self, type_name: str = "BusStation_LOD1"):
        """
        Create a simple LOD1 bus station (single box).

        Args:
            type_name: Name for the bus station element type

        Returns:
            The bus station element as BIMFactoryElement
        """
        # Create a simple box representing the entire bus station
        bus_station_box = Box(width=self.config.width, depth=self.config.depth, height=self.config.height)

        # Center the box by translating it and apply color
        return BIMFactoryElement(
            type="IfcBuildingElementProxy",
            name=type_name,
            children=[
                Style(
                    item=Transform(
                        translation=(-self.config.width / 2, -self.config.depth / 2, 0), item=bus_station_box
                    ),
                    rgb=self.config.lod2_color,
                )
            ],
        )

    def create_bus_station_lod2(self, type_name: str = "BusStation_LOD2", psets: list = None):
        """
        Create a LOD2 bus station with basic structure and 4 solid walls from floor.

        Args:
            type_name: Name for the bus station element type
            psets: List of property sets to attach to the element

        Returns:
            The bus station element as BIMFactoryElement
        """
        components = []

        # 1. Roof (top panel)
        roof = Style(
            item=Transform(
                translation=(
                    -self.config.width / 2,
                    -self.config.depth / 2,
                    self.config.height - self.config.thickness,
                ),
                item=Box(width=self.config.width, depth=self.config.depth, height=self.config.thickness),
            ),
            rgb=self.config.lod2_color,
        )
        components.append(roof)

        # 2. Three walls: left, right, and back
        # Left wall
        left_wall = Style(
            item=Transform(
                translation=(-self.config.width / 2, -self.config.depth / 2, 0),
                item=Box(
                    width=self.config.thickness,
                    depth=self.config.depth,
                    height=self.config.height - self.config.thickness,
                ),
            ),
            rgb=self.config.lod2_color,
        )
        components.append(left_wall)

        # Right wall
        right_wall = Style(
            item=Transform(
                translation=(self.config.width / 2 - self.config.thickness, -self.config.depth / 2, 0),
                item=Box(
                    width=self.config.thickness,
                    depth=self.config.depth,
                    height=self.config.height - self.config.thickness,
                ),
            ),
            rgb=self.config.lod2_color,
        )
        components.append(right_wall)

        # Back wall (between the sides)
        back_wall = Style(
            item=Transform(
                translation=(
                    -self.config.width / 2 + self.config.thickness,
                    self.config.depth / 2 - self.config.thickness,
                    0,
                ),
                item=Box(
                    width=self.config.width - 2 * self.config.thickness,
                    depth=self.config.thickness,
                    height=self.config.height - self.config.thickness,
                ),
            ),
            rgb=self.config.lod2_color,
        )
        components.append(back_wall)

        # 3. Seat
        seat = Style(
            item=Transform(
                translation=(
                    self.config.width / 2
                    - self.config.seat_width
                    - self.config.thickness,  # Move by side wall thickness
                    self.config.depth / 2
                    - self.config.seat_depth
                    - self.config.thickness,  # Move by back wall thickness
                    self.config.seat_height,
                ),
                item=Box(width=self.config.seat_width, depth=self.config.seat_depth, height=self.config.thickness),
            ),
            rgb=self.config.lod2_color,
        )
        components.append(seat)

        # Return all components as a BIMFactoryElement
        return BIMFactoryElement(type="IfcFurnitureType", name=type_name, children=components, psets=psets or [])

    def create_bus_station_lod3(self, type_name: str = "BusStation_LOD3"):
        """
        Create a detailed LOD3 bus station with separate colored components.

        Args:
            type_name: Name for the bus station element type

        Returns:
            Single BIMFactoryElement containing all bus station components
        """
        components = []

        # 1. Roof (dark gray)
        roof = Style(
            item=Transform(
                translation=(
                    -self.config.width / 2,
                    -self.config.depth / 2,
                    self.config.height - self.config.thickness,
                ),
                item=Box(width=self.config.width, depth=self.config.depth, height=self.config.thickness),
            ),
            rgb=self.config.roof_color,
        )
        components.append(roof)

        # 2. Glass panels (light blue) - sides and back
        # Left side
        left_side = Style(
            item=Transform(
                translation=(-self.config.width / 2, -self.config.depth / 2 + 0.05, 0.1),
                item=Box(
                    width=self.config.thickness,
                    depth=self.config.depth - 0.1,
                    height=self.config.height - self.config.thickness - 0.1,
                ),
            ),
            rgb=self.config.glass_color,
        )
        components.append(left_side)

        # Right side
        right_side = Style(
            item=Transform(
                translation=(self.config.width / 2 - self.config.thickness, -self.config.depth / 2 + 0.05, 0.1),
                item=Box(
                    width=self.config.thickness,
                    depth=self.config.depth - 0.1,
                    height=self.config.height - self.config.thickness - 0.1,
                ),
            ),
            rgb=self.config.glass_color,
        )
        components.append(right_side)

        # Back panel (between the sides)
        back_panel = Style(
            item=Transform(
                translation=(
                    -self.config.width / 2 + self.config.thickness,
                    self.config.depth / 2 - self.config.thickness,
                    0.1,
                ),
                item=Box(
                    width=self.config.width - 2 * self.config.thickness,
                    depth=self.config.thickness,
                    height=self.config.height - self.config.thickness - 0.1,
                ),
            ),
            rgb=self.config.glass_color,
        )
        components.append(back_panel)

        # 3. Seat (gray)
        seat = Style(
            item=Transform(
                translation=(
                    self.config.width / 2
                    - self.config.seat_width
                    - self.config.thickness,  # Move by side wall thickness
                    self.config.depth / 2
                    - self.config.seat_depth
                    - self.config.thickness,  # Move by back wall thickness
                    self.config.seat_height,
                ),
                item=Box(width=self.config.seat_width, depth=self.config.seat_depth, height=self.config.thickness),
            ),
            rgb=self.config.seat_color,
        )
        components.append(seat)

        # 4. Columns (gray)
        column = Box(
            width=self.config.frame_width,
            depth=self.config.frame_depth,
            height=self.config.height - self.config.thickness,
        )

        # Front left column
        col_fl = Style(
            item=Transform(translation=(-self.config.width / 2, -self.config.depth / 2, 0), item=column),
            rgb=self.config.columns_color,
        )
        components.append(col_fl)

        # Front right column
        col_fr = Style(
            item=Transform(
                translation=(self.config.width / 2 - self.config.frame_width, -self.config.depth / 2, 0), item=column
            ),
            rgb=self.config.columns_color,
        )
        components.append(col_fr)

        # Back left column
        col_bl = Style(
            item=Transform(
                translation=(-self.config.width / 2, self.config.depth / 2 - self.config.frame_depth, 0), item=column
            ),
            rgb=self.config.columns_color,
        )
        components.append(col_bl)

        # Back right column
        col_br = Style(
            item=Transform(
                translation=(
                    self.config.width / 2 - self.config.frame_width,
                    self.config.depth / 2 - self.config.frame_depth,
                    0,
                ),
                item=column,
            ),
            rgb=self.config.columns_color,
        )
        components.append(col_br)

        # Return all components as a single BIMFactoryElement
        return BIMFactoryElement(type="IfcBuildingElementProxy", name=type_name, children=components)


class OvalBuilder:
    """Builder class for creating oval objects using primitive geometry."""

    def __init__(
        self,
        model: ifcopenshell.file,
        body_context: ifcopenshell.entity_instance,
        config: Optional[OvalConfig] = None,
    ):
        """
        Initialize the oval builder.

        Args:
            model: The IFC model instance
            body_context: The body representation context
            config: Configuration for oval dimensions and colors
        """
        self.model = model
        self.body_context = body_context
        self.config = config or OvalConfig()
        self.shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

    def create_oval(self, type_name: str = "Oval", psets: list = None, cad_layer: str = ""):
        """
        Create an oval object using proper elliptical geometry.

        Args:
            type_name: Name for the oval element type
            psets: List of property sets to attach to the element
            cad_layer: CAD layer name for the object

        Returns:
            The oval element as BIMFactoryElement
        """
        # Create an elliptical cylinder with proper elliptical profile
        # Excel dimensions are already the semi-axes (half dimensions)
        elliptical_cylinder = EllipticalCylinder(
            semi_axis1=self.config.width,  # Use width directly as semi-axis1
            semi_axis2=self.config.depth,  # Use depth directly as semi-axis2
            height=self.config.height,
        )

        # The elliptical cylinder is already centered at the origin, so no translation needed
        return BIMFactoryElement(
            type="IfcFurnitureType",
            name=type_name,
            children=[
                Style(
                    item=elliptical_cylinder,
                    rgb=self.config.color,
                    cad_layer=cad_layer if cad_layer else type_name,
                )
            ],
            psets=psets or [],
        )


class SweepBuilder:
    """Builder class for creating sweep objects using primitive geometry."""

    def __init__(
        self,
        model: ifcopenshell.file,
        body_context: ifcopenshell.entity_instance,
        config: Optional[SweepConfig] = None,
    ):
        """
        Initialize the sweep builder.

        Args:
            model: The IFC model instance
            body_context: The body representation context
            config: Configuration for sweep dimensions and colors
        """
        self.model = model
        self.body_context = body_context
        self.config = config or SweepConfig()
        self.shape_builder = ifcopenshell.util.shape_builder.ShapeBuilder(model)

    def create_profile(self, length: float, height: float, centered: bool = True):
        """
        Create a profile curve for sweeping.

        Args:
            length: Length of the profile.
            height: Height of the profile.
            centered: Whether the profile should be centered (True for mittig, False for endpunkt).

        Returns:
            The created profile curve.
        """
        if centered:
            # Create the polyline centered at (0,0) - for "mittig"
            half_length = length / 2
            return self.shape_builder.polyline(
                [
                    (-half_length, 0.0, 0.0),  # Start at the left base
                    (-half_length, 0.0, height),  # Height at left
                    (half_length, 0.0, height),  # Height at right
                    (half_length, 0.0, 0.0),  # End at the right base
                ]
            )
        else:
            # Create the polyline starting at (0,0) - for "endpunkt"
            return self.shape_builder.polyline(
                [
                    (0.0, 0.0, 0.0),  # Start at the base (not centered)
                    (0.0, 0.0, height),  # Height of the object
                    (length, 0.0, height),  # Extend along the X-axis
                    (length, 0.0, 0.0),  # End at the base
                ]
            )

    def create_sweep(self, type_name: str = "Sweep", centered: bool = True, psets: list = None, cad_layer: str = ""):
        """
        Create a sweep object using profile curve and swept disk solid.

        Args:
            type_name: Name for the sweep element type
            centered: Whether the profile should be centered (True for mittig, False for endpunkt)
            psets: List of property sets to attach to the element
            cad_layer: CAD layer name for the object

        Returns:
            The sweep element as BIMFactoryElement
        """
        # Create the swept disk solid using our custom primitive
        swept_solid = SweptDiskSolid(
            length=self.config.length, height=self.config.height, radius=self.config.depth / 2, centered=centered
        )

        # Create the BIMFactoryElement with the swept solid
        return BIMFactoryElement(
            type="IfcFurnitureType",
            name=type_name,
            children=[
                Style(
                    item=swept_solid,
                    rgb=self.config.color,
                    cad_layer=cad_layer if cad_layer else type_name,
                )
            ],
            psets=psets or [],
        )


def create_bus_station_example():
    """Example function demonstrating how to create bus stations."""

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="BusStation_Project",
        coordinate_system="epsg_25832",
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="BusStation_Site",
        building_name="BusStation_Building",
        storey_name="BusStation_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.body

    # Create bus station builder
    config = BusStationConfig()
    builder = BusStationBuilder(model, body_context, config)

    # Create LOD1 bus station
    # The create methods already return BIMFactoryElement objects, so we just set the instance
    lod1 = builder.create_bus_station_lod1("BusStation_LOD1_001")
    lod1.inst = storey
    lod1.build(model)

    # Create LOD2 bus station
    lod2 = builder.create_bus_station_lod2("BusStation_LOD2_001")
    lod2.inst = storey
    lod2.build(model)

    # Create LOD3 bus station
    lod3 = builder.create_bus_station_lod3("BusStation_LOD3_001")
    lod3.inst = storey
    lod3.build(model)
