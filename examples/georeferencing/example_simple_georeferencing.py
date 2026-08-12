#!/usr/bin/env python3
"""
Simple example demonstrating the new simplified georeferencing system.

This example shows how easy it is to add georeferencing to IFC models
using the new CoordinateSystem model and templates.
"""

from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.core.model_creator.ifc_modelbuilder import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
    CoordinateSystemTemplates,
)

logger = get_logger()


def main():
    """Demonstrate the simplified georeferencing system."""

    # Create a model builder
    builder = IfcModelBuilder()

    logger.info("=== Simple Georeferencing Example ===\n")

    # Example 1: Use default EPSG:25832 (simplest)
    logger.info("1. Using default EPSG:25832:")
    builder.build_project(
        project_name="Default Project",
        coordinate_system="epsg_25832",
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Default Site",
        building_name="Default Building",
    )
    builder.save_ifc_to_output("example_default_georef.ifc")
    logger.info("   ✓ Saved as 'example_default_georef.ifc'\n")

    # Example 2: Use a custom coordinate system
    logger.info("3. Using custom coordinate system:")
    custom_crs = CoordinateSystem(
        name="Custom Hamburg CRS",
        geodetic_datum="ETRS89",
        description="Custom coordinate system for Hamburg area",
        vertical_datum="DHHN2016",
        map_projection="Transverse Mercator",
        map_zone="3",
    )

    # Create a custom coordinate operation with actual transformation values
    custom_operation = CoordinateOperation(
        eastings=3570605.5513,
        northings=5937434.3470,
        orthogonal_height=0.0,
        x_axis_abscissa=0.0,
        x_axis_ordinate=0.0,
        scale=1.0,
    )

    builder.reset_model()
    builder.build_project(
        project_name="Custom Project",
        coordinate_system=custom_crs,
        coordinate_operation=custom_operation,
        site_name="Custom Site",
        building_name="Custom Building",
    )
    builder.save_ifc_to_output("example_custom_georef.ifc")
    logger.info("   ✓ Saved as 'example_custom_georef.ifc'\n")

    # Example 3b: Use custom coordinate system with custom operation
    logger.info("3b. Using custom coordinate system with custom transformation:")
    builder.reset_model()
    # Use the build_project method which handles the proper order of operations
    builder.build_project(
        project_name="Custom Transform Project",
        coordinate_system=custom_crs,
        coordinate_operation=custom_operation,
        site_name="Custom Transform Site",
        building_name="Custom Transform Building",
    )
    # Note: The coordinate operation is currently handled internally with defaults
    # For custom operations, you would need to extend the build_project method
    builder.save_ifc_to_output("example_custom_transform_georef.ifc")
    logger.info("   ✓ Saved as 'example_custom_transform_georef.ifc'\n")

    # Example 4: Use Gauß-Krüger Hamburg template
    logger.info("4. Using Gauß-Krüger Hamburg template:")
    builder.reset_model()
    builder.build_project(
        project_name="Hamburg Project",
        coordinate_system="gauss_kruger_hamburg",
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Hamburg Site",
        building_name="Hamburg Building",
    )
    builder.save_ifc_to_output("example_hamburg_georef.ifc")
    logger.info("   ✓ Saved as 'example_hamburg_georef.ifc'\n")

    logger.info("=== All examples completed successfully! ===")
    logger.info("Check the 'output' directory for the generated IFC files.")


if __name__ == "__main__":
    setup_logging()
    main()
