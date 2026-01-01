"""
Comprehensive Example: All BIMFabrikHH Examples Combined
=======================================================

This example demonstrates all the major functionalities of BIMFabrikHH
by importing and running all the existing example functions from the
various example directories.

Features demonstrated:
- Basepoint creation with north arrow
- City model processing from XML files
- Tree modeling with elevation data
- Terrain/DGM creation
- City furniture (bus stations)
- Primitive geometry objects
- Standard profiles
- Georeferencing
- Pydantic data models
- Modular apps with clean interfaces

Usage:
    python all_examples.py

This will create multiple IFC files demonstrating different aspects of the library.
"""

import os
import time
from pathlib import Path

from city_furniture.example_bus_stations import main as create_city_furniture
from city_model.basic.example_basic_city_model import main as create_city_model
from city_model.from_xml.example_city_model_from_xml import main as create_city_model_from_xml
from city_model.generic.example_generic_city_model import main as create_city_model_generic
from city_model.modular.example_modular_city import main as create_city_model_modular
from city_model.timing.example_city_model_timing import main as create_city_model_timing
from city_model.with_pydantic.example_city_model_with_pydantic import main as create_city_model_with_pydantic
from city_model.with_pydantic.simple_example import main as create_city_model_simple
from georeferencing.example_enhanced_georeferencing import main as create_georeferencing_enhanced
from georeferencing.example_simple_georeferencing import main as create_georeferencing
from primitive_objects.example_all_primitives_with_tree_and_dgm import main as create_primitives_all
from primitive_objects.example_basic_primitives import main as create_primitives_basic
from primitive_objects.example_boolean_operations import main as create_primitives_boolean
from primitive_objects.example_complex_assemblies import main as create_primitives_assemblies
from primitive_objects.example_materials_and_styles import main as create_primitives_materials
from primitive_objects.example_ngon_cylinders import main as create_primitives_ngon_cylinders
from primitive_objects.example_property_sets import main as create_primitives_psets
from primitive_objects.example_transformations import main as create_primitives_transformations
from terrain.basic.example_basic_terrain import main as create_terrain
from terrain.filtered.example_filtered_terrain import main as create_terrain_filtered
from terrain.modular.example_modular_terrain import main as create_terrain_modular
from terrain.optimized.example_optimized_terrain import main as create_terrain_optimized
from trees.basic.example_basic_trees import main as create_trees
from trees.combined.example_combined_trees import main as create_trees_combined
from trees.generic.example_generic_trees import main as create_trees_generic
from trees.optimized.example_optimized_trees import main as create_trees_optimized

from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()


def run_comprehensive_examples():
    """Run all examples in sequence by importing their main functions."""
    print("BIMFabrikHH Comprehensive Example")
    print("=" * 60)
    print("This example demonstrates all major functionalities of BIMFabrikHH")
    print("by importing and running all existing example functions.")
    print("=" * 60)

    start_time = time.perf_counter()

    # Create output directory if it doesn't exist
    PathConfig.OUTPUT.mkdir(exist_ok=True)

    # Store original working directory
    original_cwd = Path.cwd()

    try:
        # Change to examples directory to ensure relative paths work correctly
        examples_dir = Path(__file__).parent
        os.chdir(examples_dir)

        print("\n=== Running City Model Examples ===")
        print("--- Basic City Model ---")
        create_city_model()
        print("--- City Model from XML ---")
        create_city_model_from_xml()
        print("--- Generic City Model ---")
        create_city_model_generic()
        print("--- City Model Timing ---")
        create_city_model_timing()
        print("--- City Model with Pydantic ---")
        create_city_model_with_pydantic()
        print("--- City Model Simple Example ---")
        create_city_model_simple()
        print("--- Modular City Model ---")
        create_city_model_modular()

        print("\n=== Running Trees Examples ===")
        print("--- Basic Trees ---")
        create_trees()
        print("--- Combined Trees ---")
        create_trees_combined()
        print("--- Generic Trees ---")
        create_trees_generic()
        print("--- Optimized Trees ---")
        create_trees_optimized()

        print("\n=== Running Terrain Examples ===")
        print("--- Basic Terrain ---")
        create_terrain()
        print("--- Filtered Terrain ---")
        create_terrain_filtered()
        print("--- Optimized Terrain ---")
        create_terrain_optimized()
        print("--- Modular Terrain ---")
        create_terrain_modular()

        print("\n=== Running City Furniture Example ===")
        create_city_furniture()

        print("\n=== Running Primitive Objects Examples ===")
        print("--- Basic Primitives ---")
        create_primitives_basic()
        print("--- Boolean Operations ---")
        create_primitives_boolean()
        print("--- Complex Assemblies ---")
        create_primitives_assemblies()
        print("--- Materials and Styles ---")
        create_primitives_materials()
        print("--- N-gon Cylinders ---")
        create_primitives_ngon_cylinders()
        print("--- Property Sets ---")
        create_primitives_psets()
        print("--- Transformations ---")
        create_primitives_transformations()
        print("--- All Primitives with Tree and DGM ---")
        create_primitives_all()

        print("\n=== Running Georeferencing Examples ===")
        print("--- Simple Georeferencing ---")
        create_georeferencing()
        print("--- Enhanced Georeferencing ---")
        create_georeferencing_enhanced()

    except Exception as e:
        logger.error(f"Error during example execution: {e}")
        import traceback

        traceback.print_exc()
        return

    finally:
        # Restore original working directory
        os.chdir(original_cwd)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    print("\n" + "=" * 60)
    print("COMPREHENSIVE EXAMPLE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total execution time: {total_time:.2f} seconds")
    print("\nAll example files have been created in their respective directories.")
    print("You can now open these IFC files in any BIM software that supports IFC format.")
    print("\nGenerated files include:")
    print("  ✓ Basepoint with north arrow (basic)")
    print("  ✓ Basepoint with Pydantic data models")
    print("  ✓ City model from XML files (basic, from_xml, generic, primitive, timing, pydantic, modular)")
    print("  ✓ Tree models (basic, combined, generic, optimized, pydantic)")
    print("  ✓ Digital ground model (basic, filtered, optimized, modular)")
    print("  ✓ Bus station with multiple LODs")
    print("  ✓ Complex geometric shapes (primitives suite)")
    print("  ✓ All primitives with tree and DGM")
    print("  ✓ Various profile types")
    print("  ✓ Multiple georeferencing examples (simple, enhanced)")
    print("  ✓ Modular city model with clean interface")
    print("  ✓ Modular terrain with clean interface")


if __name__ == "__main__":
    run_comprehensive_examples()
