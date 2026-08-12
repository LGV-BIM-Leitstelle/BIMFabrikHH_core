"""
Example demonstrating the enhanced georeferencing system with coordinate system models.

Every project is bootstrapped via :func:`init_ifc_project`, which provides
sensible defaults for ``coordinate_operation`` and the EPSG:25832 CRS so
each example only has to declare the coordinate system it actually cares
about.

This example shows:

1. Using predefined CRS templates.
2. Creating a custom :class:`CoordinateSystem`.
3. The enhanced georeferencing model (``epsg_25832`` via templates).
4. The default EPSG:25832 fallback of :func:`init_ifc_project`.
5. Retrieving the CRS back from the written model.
"""

from pathlib import Path

from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateSystem,
    CoordinateSystemTemplates,
)

logger = get_logger()


def example_using_templates():
    """Example using predefined coordinate system templates.

    Walks through every template registered on
    :class:`CoordinateSystemTemplates` (``epsg_25832``, ``epsg_25833``,
    ``gauss_kruger_hamburg``) so the output reflects what ``get_template``
    actually supports.
    """
    logger.info("=== Example 1: Using Predefined Templates ===")

    logger.info("\n1. Creating project with EPSG:25832 (ETRS89 / UTM zone 32N)...")
    builder = init_ifc_project(
        project_name="EPSG25832 Project",
        site_name="EPSG25832 Site",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
    )
    builder.save_ifc_to_output("example_epsg25832.ifc")
    logger.info("OK Saved EPSG:25832 project")

    logger.info("\n2. Creating project with EPSG:25833 (ETRS89 / UTM zone 33N)...")
    builder = init_ifc_project(
        project_name="EPSG25833 Project",
        site_name="EPSG25833 Site",
        coordinate_system=CoordinateSystemTemplates.epsg_25833(),
    )
    builder.save_ifc_to_output("example_epsg25833.ifc")
    logger.info("OK Saved EPSG:25833 project")

    logger.info("\n3. Creating project with Gauss-Krueger Hamburg coordinate system...")
    builder = init_ifc_project(
        project_name="GaussKruger Project",
        site_name="GaussKruger Site",
        coordinate_system=CoordinateSystemTemplates.gauss_kruger_hamburg(),
    )
    builder.save_ifc_to_output("example_gauss_kruger_hamburg.ifc")
    logger.info("OK Saved Gauss-Krueger Hamburg project")


def example_custom_coordinate_system():
    """Example creating a custom coordinate system."""
    logger.info("\n=== Example 2: Custom Coordinate System ===")

    custom_crs = CoordinateSystem(
        name="Custom Local CRS",
        description="Custom coordinate system for local project area",
        geodetic_datum="ETRS89",
        vertical_datum="DHHN2016",
        map_projection="Transverse Mercator",
        map_zone="31",
    )

    builder = init_ifc_project(
        project_name="Custom CRS Project",
        site_name="Custom CRS Site",
        coordinate_system=custom_crs,
    )
    builder.save_ifc_to_output("example_custom_crs.ifc")
    logger.info("OK Saved custom coordinate system project")


def example_enhanced_georeferencing():
    """Example using the enhanced georeferencing model."""
    logger.info("\n=== Example 3: Enhanced Georeferencing Model ===")

    builder = init_ifc_project(
        project_name="Enhanced Georef Project",
        site_name="Enhanced Georef Site",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
    )
    builder.save_ifc_to_output("example_enhanced_georef.ifc")
    logger.info("OK Saved enhanced georeferencing project")


def example_default_crs_fallback():
    """Example showing the EPSG:25832 fallback when no CRS is supplied.

    :func:`init_ifc_project` treats ``coordinate_system`` and
    ``coordinate_operation`` as optional: omit both and you get
    EPSG:25832 with the identity coordinate operation — the BIM.HH
    house default. Handy for quick prototyping in the project CRS.
    """
    logger.info("\n=== Example 4: Default CRS (EPSG:25832 Fallback) ===")

    # No coordinate_system argument — init_ifc_project defaults to EPSG:25832.
    builder = init_ifc_project(
        project_name="Default Georef Project",
        site_name="Default Georef Site",
    )
    builder.save_ifc_to_output("example_default_georef.ifc")
    logger.info("OK Saved default-CRS project (EPSG:25832 fallback)")


def example_coordinate_system_retrieval():
    """Example showing how to retrieve coordinate system from an existing model.

    The CRS is persisted as ``IfcProjectedCRS`` by
    :meth:`IfcModelMethods.edit_georeference`; reading it back is a plain
    ``model.by_type("IfcProjectedCRS")`` lookup — no extra helper required.
    """
    logger.info("\n=== Example 5: Coordinate System Retrieval ===")

    builder = init_ifc_project(
        project_name="Retrieval Test Project",
        site_name="Retrieval Test Site",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
    )

    projected_crs_entities = builder.model.by_type("IfcProjectedCRS")
    if not projected_crs_entities:
        logger.warning("No IfcProjectedCRS entity found in model")
        return

    projected_crs = projected_crs_entities[0]
    retrieved_crs = CoordinateSystem(
        name=projected_crs.Name,
        description=projected_crs.Description,
        geodetic_datum=projected_crs.GeodeticDatum,
        vertical_datum=projected_crs.VerticalDatum,
        map_projection=projected_crs.MapProjection,
        map_zone=projected_crs.MapZone,
    )

    logger.info("Retrieved coordinate system:")
    logger.info(f"  Name: {retrieved_crs.name}")
    logger.info(f"  Description: {retrieved_crs.description}")
    logger.info(f"  Geodetic Datum: {retrieved_crs.geodetic_datum}")
    logger.info(f"  Map Projection: {retrieved_crs.map_projection}")
    logger.info(f"  Map Zone: {retrieved_crs.map_zone}")

    builder.save_ifc_to_output("example_retrieval_test.ifc")
    logger.info("OK Saved retrieval test project")


def main():
    """Run all examples."""
    logger.info("Enhanced Georeferencing System Examples")
    logger.info("=" * 50)

    try:
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        example_using_templates()
        example_custom_coordinate_system()
        example_enhanced_georeferencing()
        example_default_crs_fallback()
        example_coordinate_system_retrieval()

        logger.info("\n" + "=" * 50)
        logger.info("All examples completed successfully!")
        logger.info("Check the 'output' directory for generated IFC files.")

    except Exception as e:
        logger.error(f"Error running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    setup_logging()
    main()
