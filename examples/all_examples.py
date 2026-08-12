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

from basepoint.example_basepoint_basic import main as create_basepoint_basic
from basepoint.example_basepoint_generic import main as create_basepoint_generic
from city_furniture.example_bus_stations import main as create_city_furniture
from city_model.basic.example_basic_city_model import main as create_city_model_basic
from city_model.generic.example_generic_city_model import (
    main as create_city_model_generic,
)
from georeferencing.example_enhanced_georeferencing import (
    main as create_georeferencing_enhanced,
)
from georeferencing.example_simple_georeferencing import main as create_georeferencing
from terrain.basic.example_basic_terrain import main as create_terrain_basic
from terrain.generic.example_generic_terrain import main as create_terrain_generic
from trees.basic.example_basic_trees import main as create_trees_basic
from trees.generic.example_trees_generic import main as create_trees_generic

from BIMFabrikHH_core.config import get_logger, setup_logging
from BIMFabrikHH_core.config.paths import PathConfig

logger = get_logger()


def run_comprehensive_examples() -> None:
    """Run all in-repo example ``main()`` functions in sequence."""
    logger.info("BIMFabrikHH Comprehensive Example")
    logger.info("=" * 60)
    logger.info("Runs every in-repo example main() in a single pass.")
    logger.info("=" * 60)

    start_time = time.perf_counter()

    PathConfig.OUTPUT.mkdir(exist_ok=True)

    original_cwd = Path.cwd()

    try:
        # Some examples resolve asset paths relative to the examples/ folder.
        examples_dir = Path(__file__).parent
        os.chdir(examples_dir)

        logger.info("\n=== Basepoint Examples ===")
        logger.info("--- Basic Basepoint ---")
        create_basepoint_basic()
        logger.info("--- Generic Basepoint (ifcfactory) ---")
        create_basepoint_generic()

        logger.info("\n=== City Model Examples ===")
        logger.info("--- Basic City Model ---")
        create_city_model_basic()
        logger.info("--- Generic City Model (ifcfactory) ---")
        create_city_model_generic()

        logger.info("\n=== Trees Examples ===")
        logger.info("--- Basic Trees ---")
        create_trees_basic()
        logger.info("--- Generic Trees (ifcfactory) ---")
        create_trees_generic()

        logger.info("\n=== Terrain Examples ===")
        logger.info("--- Basic Terrain (adaptive-sampled DGM) ---")
        create_terrain_basic()
        logger.info("--- Generic Terrain (ifcfactory) ---")
        create_terrain_generic()

        logger.info("\n=== City Furniture Example ===")
        create_city_furniture()

        logger.info("\n=== Georeferencing Examples ===")
        logger.info("--- Simple Georeferencing ---")
        create_georeferencing()
        logger.info("--- Enhanced Georeferencing ---")
        create_georeferencing_enhanced()

    except Exception as exc:
        logger.error(f"Error during example execution: {exc}")
        import traceback

        traceback.print_exc()
        return

    finally:
        os.chdir(original_cwd)

    total_time = time.perf_counter() - start_time

    logger.info("\n" + "=" * 60)
    logger.info("COMPREHENSIVE EXAMPLE COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info(f"Total execution time: {total_time:.2f} seconds")
    logger.info("\nAll example files have been created under PathConfig.OUTPUT.")
    logger.info("Open them in any BIM software that supports IFC.")
    logger.info("\nGenerated files include:")
    logger.info("  - Basepoint with north arrow (basic + generic)")
    logger.info("  - City model (basic + generic / ifcfactory)")
    logger.info("  - Tree models (basic + generic)")
    logger.info("  - Digital ground model (basic + generic)")
    logger.info("  - Bus station with multiple LODs")
    logger.info("  - Simple and enhanced georeferencing")


if __name__ == "__main__":
    setup_logging()
    run_comprehensive_examples()
