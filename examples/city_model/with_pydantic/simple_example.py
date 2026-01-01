"""
Simple Example: Using CityModelAttributes Pydantic Model

This example shows how to use the new CityModelAttributes Pydantic model
without changing the existing city model app code.
"""

from BIMFabrikHH_core.data_models.pydantic_psets_city_model import CityModelAttributes


def main():
    """Simple example of using CityModelAttributes."""

    print("=== Simple CityModelAttributes Example ===\n")

    # Example 1: Basic usage (as shown in the user's example)
    print("1. Basic usage:")
    obj = CityModelAttributes(id_ebene1="Stadtmodell", loi=300)
    print(f"   Object: {obj}")
    print(f"   Serialized with aliases: {obj.model_dump(by_alias=True)}")
    print()

    # Example 2: Using the same field names as the app
    print("2. Using app field names:")
    obj2 = CityModelAttributes(id_ebene1="Wohngebaeude", relative_hoehe=15.5, anzahl_obergeschoss=5)
    print(f"   Object: {obj2}")
    print(f"   Serialized with aliases: {obj2.model_dump(by_alias=True)}")
    print()

    # Example 3: Accessing fields directly
    print("3. Accessing fields:")
    print(f"   id_ebene1: {obj2.id_ebene1}")
    print(f"   relative_hoehe: {obj2.relative_hoehe}")
    print(f"   anzahl_obergeschoss: {obj2.anzahl_obergeschoss}")
    print()

    # Example 4: Default values
    print("4. Default values:")
    default_obj = CityModelAttributes()
    print(f"   Default object: {default_obj}")
    print("   All fields are None by default")
    print()

    print("=== Key Points ===")
    print("✓ Field names match the existing app (relative_hoehe, anzahl_obergeschoss)")
    print("✓ Serialization aliases are used for IFC export (_IDEbene1, _LoI, etc.)")
    print("✓ No changes needed to existing app code")
    print("✓ Simple and straightforward usage")


if __name__ == "__main__":
    main()
