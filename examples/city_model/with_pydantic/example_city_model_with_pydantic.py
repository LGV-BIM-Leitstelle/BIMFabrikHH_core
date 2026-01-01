"""
Example: Using CityModelAttributes Pydantic Model with City Model App

This example demonstrates how to use the new CityModelAttributes Pydantic model
for handling building attributes in the city model application.
"""

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import (
    CityModelAttributes,
    CityModelBuildingData,
    create_city_model_attributes,
    get_default_city_model_attributes,
)

logger = get_logger()


def demonstrate_pydantic_usage():
    """Demonstrate various ways to use the CityModelAttributes Pydantic model."""

    print("=== CityModelAttributes Pydantic Model Examples ===\n")

    # Example 1: Basic usage (as shown in the user's example)
    print("1. Basic usage:")
    obj = CityModelAttributes(id_ebene1="Stadtmodell", loi=300)
    print(f"   Object: {obj}")
    print(f"   Serialized: {obj.model_dump(by_alias=True)}")
    print()

    # Example 2: Complete building data
    print("2. Complete building data:")
    from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

    building_data = CityModelBuildingData(
        buildings=[
            Building(
                id="BUILDING_001",
                attributes=CityModelAttributes(
                    id_ebene1="Wohngebaeude",
                    id_ebene2="Mehrfamilienhaus",
                    loi=300,
                    stadtmodell_lod="LOD1",
                    funktion_gebaeude="Wohnen",
                    anzahl_obergeschoss=5,
                    dachform="Flachdach",
                ),
                vertices=[(0, 0, 0), (10, 0, 0), (10, 10, 0), (0, 10, 0)],
                faces=[[0, 1, 2, 3]],
            )
        ],
    )
    print(f"   Building data: {building_data}")
    print()

    # Example 3: Using convenience function
    print("3. Using convenience function:")
    attrs = create_city_model_attributes(id_ebene1="Gewerbe", loi=400, funktion_gebaeude="Büro", anzahl_obergeschoss=8)
    print(f"   Attributes: {attrs}")
    print()

    # Example 4: Default attributes
    print("4. Default attributes:")
    default_attrs = get_default_city_model_attributes()
    print(f"   Default: {default_attrs}")
    print()

    # Example 5: Validation and error handling
    print("5. Validation example:")
    try:
        # This will work
        valid_attrs = CityModelAttributes(id_ebene1="Stadtmodell", loi=300, anzahl_obergeschoss=5)
        print(f"   Valid attributes: {valid_attrs}")

        # This will also work (optional fields)
        minimal_attrs = CityModelAttributes()
        print(f"   Minimal attributes: {minimal_attrs}")

    except Exception as e:
        print(f"   Validation error: {e}")
    print()


def demonstrate_city_model_processing():
    """Demonstrate how the Pydantic model integrates with city model processing."""

    print("=== City Model Processing with Pydantic ===\n")

    # Example: Process city model files with the new Pydantic integration
    # citymodel_folder = Path(__file__).parent
    xml_files = [
        "LoD1_32_549_5935_1_HH.xml",
        "LoD1_32_549_5936_1_HH.xml",
        "LoD1_32_549_5937_1_HH.xml",
        "LoD1_32_549_5938_1_HH.xml",
    ]

    # Create container with Pydantic-aware components
    container = Container(
        containerTitle="Citymodel_Container_With_Pydantic",
        containerId="citymodel_pydantic",
        components={
            "description": Component(title="Description", value="Hamburg City Model with Pydantic Attributes"),
            "type": Component(title="Model Type", value="LoD1 Building Models with Pydantic"),
            "pydantic_version": Component(title="Pydantic Version", value="2.x"),
        },
    )

    # Create request parameters
    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.7500, min_y=53.5813, max_x=9.7483, max_y=53.5856), containers=[container]
    )

    print("Processing city model files with Pydantic integration...")
    print(f"Files: {xml_files}")
    print(f"Bounding box: {request_body.bbox}")
    print()

    # Note: This would actually process the files if they exist
    # For demonstration, we'll just show the structure
    print("The city model app now uses CityModelAttributes for:")
    print("- Building identification (id_ebene1, id_ebene2, id_ebene3)")
    print("- Building properties (loi, bemerkung, stadtmodell_lod)")
    print("- Building function (funktion_gebaeude)")
    print("- Building dimensions (relative_hoehe, anzahl_obergeschoss)")
    print("- Building form (dachform)")
    print("- Additional properties (relative_hoehe, anzahl_obergeschoss)")
    print()

    print("Each building extracted from CityGML will have:")
    print("- Default values set automatically")
    print("- Proper serialization aliases for IFC export")
    print("- Type validation and error handling")
    print("- Backward compatibility with existing code")


def demonstrate_ifc_integration():
    """Demonstrate how the Pydantic model integrates with IFC property sets."""

    print("=== IFC Integration with Pydantic ===\n")

    # Example: How the attributes would be used in IFC property sets
    building_attrs = CityModelAttributes(
        id_ebene1="Wohngebaeude",
        id_ebene2="Mehrfamilienhaus",
        loi=300,
        stadtmodell_lod="LOD1",
        funktion_gebaeude="Wohnen",
        anzahl_obergeschoss=5,
        dachform="Flachdach",
    )

    # Get the attributes as a dictionary with proper serialization aliases
    ifc_property_data = building_attrs.model_dump(by_alias=True)

    print("IFC Property Set Data (with serialization aliases):")
    for key, value in ifc_property_data.items():
        if value is not None:
            print(f"  {key}: {value}")
    print()

    print("This data can be directly used to create IFC property sets:")
    print("- Pset_Objektinformation for building classification")
    print("- Pset_BuildingCommonProperties for building properties")
    print("- Custom property sets for city model specific data")


def main():
    """Main function to run all demonstrations."""

    print("CityModelAttributes Pydantic Model Integration Examples")
    print("=" * 60)
    print()

    # Demonstrate basic Pydantic usage
    demonstrate_pydantic_usage()

    # Demonstrate city model processing integration
    demonstrate_city_model_processing()

    # Demonstrate IFC integration
    demonstrate_ifc_integration()

    print("=" * 60)
    print("Examples completed successfully!")
    print()
    print("Key benefits of using CityModelAttributes:")
    print("✓ Type safety and validation")
    print("✓ Automatic serialization with proper aliases")
    print("✓ Easy integration with existing code")
    print("✓ Consistent data structure across the application")
    print("✓ Default values and optional fields")
    print("✓ Backward compatibility")


if __name__ == "__main__":
    main()
