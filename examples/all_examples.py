"""
Comprehensive Example: All BIMFabrikHH Examples Combined
=======================================================

Runs every in-repo example ``main()`` in sequence so a single command
produces the full suite of demo IFC files under
``PathConfig.OUTPUT``. Useful as a smoke test after refactors and as a
one-shot regeneration of the tutorial artefacts.

Features demonstrated:

- Basepoint creation with north arrow (basic + generic)
- City model from CityGML tiles (basic + generic / ``ifcfactory``)
- Tree modelling (basic + generic / ``ifcfactory``)
- Terrain / DGM creation (basic + generic / ``ifcfactory``)
- City furniture (bus stations)
- Simple and enhanced georeferencing

Usage::

    python all_examples.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from basepoint.example_basepoint_basic import main as create_basepoint_basic
from basepoint.example_basepoint_generic import main as create_basepoint_generic
from city_furniture.example_bus_stations import main as create_city_furniture
from city_model.basic.example_basic_city_model import main as create_city_model_basic
from city_model.generic.example_generic_city_model import main as create_city_model_generic
from georeferencing.example_enhanced_georeferencing import main as create_georeferencing_enhanced
from georeferencing.example_simple_georeferencing import main as create_georeferencing
from terrain.basic.example_basic_terrain import main as create_terrain_basic
from terrain.generic.example_generic_terrain import main as create_terrain_generic
from trees.basic.example_basic_trees import main as create_trees_basic
from trees.generic.example_trees_generic import main as create_trees_generic

logger = get_logger()


def run_comprehensive_examples() -> None:
    """Run all in-repo example ``main()`` functions in sequence."""
    print("BIMFabrikHH Comprehensive Example")
    print("=" * 60)
    print("Runs every in-repo example main() in a single pass.")
    print("=" * 60)

    start_time = time.perf_counter()

    PathConfig.OUTPUT.mkdir(exist_ok=True)

    original_cwd = Path.cwd()

    try:
        # Some examples resolve asset paths relative to the examples/ folder.
        examples_dir = Path(__file__).parent
        os.chdir(examples_dir)

        print("\n=== Basepoint Examples ===")
        print("--- Basic Basepoint ---")
        create_basepoint_basic()
        print("--- Generic Basepoint (ifcfactory) ---")
        create_basepoint_generic()

        print("\n=== City Model Examples ===")
        print("--- Basic City Model ---")
        create_city_model_basic()
        print("--- Generic City Model (ifcfactory) ---")
        create_city_model_generic()

        print("\n=== Trees Examples ===")
        print("--- Basic Trees ---")
        create_trees_basic()
        print("--- Generic Trees (ifcfactory) ---")
        create_trees_generic()

        print("\n=== Terrain Examples ===")
        print("--- Basic Terrain (adaptive-sampled DGM) ---")
        create_terrain_basic()
        print("--- Generic Terrain (ifcfactory) ---")
        create_terrain_generic()

        print("\n=== City Furniture Example ===")
        create_city_furniture()

        print("\n=== Georeferencing Examples ===")
        print("--- Simple Georeferencing ---")
        create_georeferencing()
        print("--- Enhanced Georeferencing ---")
        create_georeferencing_enhanced()

    except Exception as exc:
        logger.error(f"Error during example execution: {exc}")
        import traceback

        traceback.print_exc()
        return

    finally:
        os.chdir(original_cwd)

    total_time = time.perf_counter() - start_time

    print("\n" + "=" * 60)
    print("COMPREHENSIVE EXAMPLE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Total execution time: {total_time:.2f} seconds")
    print("\nAll example files have been created under PathConfig.OUTPUT.")
    print("Open them in any BIM software that supports IFC.")
    print("\nGenerated files include:")
    print("  - Basepoint with north arrow (basic + generic)")
    print("  - City model (basic + generic / ifcfactory)")
    print("  - Tree models (basic + generic)")
    print("  - Digital ground model (basic + generic)")
    print("  - Bus station with multiple LODs")
    print("  - Simple and enhanced georeferencing")


if __name__ == "__main__":
    run_comprehensive_examples()
