"""
Example: Bus Station Objects
============================

This example demonstrates how to create bus station objects using
the city_furniture module with primitive geometry.
"""

from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.core.geometry.city_furniture import (
    BusStationBuilder,
    BusStationConfig,
    create_bus_station_example,
)
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateSystemTemplates,
)

logger = get_logger()


def main():
    """Create bus stations with different LODs using primitive objects."""

    logger.info("Creating bus station example...")
    create_bus_station_example()

    logger.info("Creating custom bus station...")
    create_custom_bus_station()


def create_custom_bus_station():
    """Create a custom bus station with modified configuration."""

    # Create model and contexts
    model_builder = IfcModelBuilder()
    coordinate_system = CoordinateSystemTemplates.epsg_25832()
    model_builder.build_project(
        project_name="Custom_BusStation_Project",
        coordinate_system=coordinate_system,
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Custom_BusStation_Site",
        building_name="Custom_BusStation_Building",
        storey_name="Custom_BusStation_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.body

    # Create custom configuration
    custom_config = BusStationConfig(
        width=5.0,  # Wider bus station
        depth=2.0,  # Deeper bus station
        height=3.0,  # Taller bus station
        seat_width=2.5,  # Wider seating area
        seat_depth=0.5,  # Deeper seating area
        seat_height=0.6,  # Higher seating
        # Custom colors
        lod2_color=(0.8, 0.2, 0.8),  # Purple
        roof_color=(0.3, 0.3, 0.3),  # Darker gray
        seat_color=(0.6, 0.4, 0.2),  # Brown
        glass_color=(0.9, 0.95, 1.0),  # Very light blue
        columns_color=(0.4, 0.4, 0.4),  # Darker gray
    )

    # Create bus station builder with custom config
    builder = BusStationBuilder(model, body_context, custom_config)

    # Create LOD1 bus station
    # The create methods already return BIMFactoryElement objects, so we just set the instance
    lod1 = builder.create_bus_station_lod1("BusStation_LOD1")
    lod1.inst = storey
    lod1.build(model)

    # Create LOD2 bus station
    lod2 = builder.create_bus_station_lod2("BusStation_LOD2")
    lod2.inst = storey
    lod2.build(model)

    # Create LOD3 bus station
    lod3 = builder.create_bus_station_lod3("BusStation_LOD3")
    lod3.inst = storey
    lod3.build(model)

    output_file = "bus_station_example.ifc"
    model.write(output_file)

    logger.info(f"bus station IFC model created successfully: {output_file}")


if __name__ == "__main__":
    setup_logging()
    main()
