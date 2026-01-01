"""
Example demonstrating the enhanced georeferencing system with coordinate system models.

This example shows how to use the new coordinate system functionality:
1. Using predefined templates
2. Creating custom coordinate systems
3. Using the enhanced georeferencing model
"""

from pathlib import Path

from BIMFabrikHH_core.core.model_creator.ifc_modelbuilder import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystem, CoordinateSystemTemplates


def example_using_templates():
    """Example using predefined coordinate system templates."""
    print("=== Example 1: Using Predefined Templates ===")

    # Create model builder
    builder = IfcModelBuilder()

    # Example 1: Using WGS84 template
    print("\n1. Creating project with WGS84 coordinate system...")
    builder.build_project(project_name="WGS84 Project", site_name="WGS84 Site", coordinate_system="wgs84")
    builder.save_ifc_to_output("example_wgs84.ifc")
    print("✓ Saved WGS84 project")

    # Reset for next example
    builder.reset_model()

    # Example 2: Using EPSG:25832 template
    print("\n2. Creating project with EPSG:25832 coordinate system...")
    builder.build_project(project_name="EPSG25832 Project", site_name="EPSG25832 Site", coordinate_system="epsg_25832")
    builder.save_ifc_to_output("example_epsg25832.ifc")
    print("✓ Saved EPSG:25832 project")

    # Reset for next example
    builder.reset_model()

    # Example 3: Using Gauß-Krüger Hamburg template
    print("\n3. Creating project with Gauß-Krüger Hamburg coordinate system...")
    builder.build_project(
        project_name="GaussKruger Project", site_name="GaussKruger Site", coordinate_system="gauss_kruger_hamburg"
    )
    builder.save_ifc_to_output("example_gauss_kruger_hamburg.ifc")
    print("✓ Saved Gauß-Krüger Hamburg project")


def example_custom_coordinate_system():
    """Example creating a custom coordinate system."""
    print("\n=== Example 2: Custom Coordinate System ===")

    # Create a custom coordinate system for a specific location
    custom_crs = CoordinateSystem(
        name="Custom Local CRS",
        description="Custom coordinate system for local project area",
        geodetic_datum="ETRS89",
        vertical_datum="DHHN2016",
        map_projection="Transverse Mercator",
        map_zone="31",
    )

    # Create model with custom coordinate system
    builder = IfcModelBuilder()
    builder.build_project(project_name="Custom CRS Project", site_name="Custom CRS Site", coordinate_system=custom_crs)
    builder.save_ifc_to_output("example_custom_crs.ifc")
    print("✓ Saved custom coordinate system project")


def example_enhanced_georeferencing():
    """Example using the enhanced georeferencing model."""
    print("\n=== Example 3: Enhanced Georeferencing Model ===")

    # Create coordinate system
    coord_sys = CoordinateSystemTemplates.epsg_25832()

    # Create model with coordinate system
    builder = IfcModelBuilder()
    builder.build_project(
        project_name="Enhanced Georef Project", site_name="Enhanced Georef Site", coordinate_system=coord_sys
    )
    builder.save_ifc_to_output("example_enhanced_georef.ifc")
    print("✓ Saved enhanced georeferencing project")


def example_backward_compatibility():
    """Example showing backward compatibility with default georeferencing."""
    print("\n=== Example 4: Backward Compatibility ===")

    # Create model without specifying coordinate system (uses default)
    builder = IfcModelBuilder()
    builder.build_project(
        project_name="Default Georef Project",
        site_name="Default Georef Site",
        # No coordinate_system parameter - uses default
    )
    builder.save_ifc_to_output("example_default_georef.ifc")
    print("✓ Saved default georeferencing project (backward compatible)")


def example_coordinate_system_retrieval():
    """Example showing how to retrieve coordinate system from existing model."""
    print("\n=== Example 5: Coordinate System Retrieval ===")

    # First create a model with a specific coordinate system
    builder = IfcModelBuilder()
    builder.build_project(
        project_name="Retrieval Test Project", site_name="Retrieval Test Site", coordinate_system="epsg_25832"
    )

    # Retrieve the coordinate system from the model
    retrieved_crs = builder.ifc_creator.get_coordinate_system_from_model(builder.model)

    print("Retrieved coordinate system:")
    print(f"  Name: {retrieved_crs.name}")
    print(f"  Description: {retrieved_crs.description}")
    print(f"  Geodetic Datum: {retrieved_crs.geodetic_datum}")
    print(f"  Map Projection: {retrieved_crs.map_projection}")
    print(f"  Map Zone: {retrieved_crs.map_zone}")
    print(f"  Map Zone: {retrieved_crs.map_zone}")

    builder.save_ifc_to_output("example_retrieval_test.ifc")
    print("✓ Saved retrieval test project")


def main():
    """Run all examples."""
    print("Enhanced Georeferencing System Examples")
    print("=" * 50)

    try:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        # Run all examples
        example_using_templates()
        example_custom_coordinate_system()
        example_enhanced_georeferencing()
        example_backward_compatibility()
        example_coordinate_system_retrieval()

        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("Check the 'output' directory for generated IFC files.")

    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
