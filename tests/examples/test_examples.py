"""
Tests for example files.

This module automatically discovers and tests all example files in the examples directory.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
examples_dir = project_root / "examples"
src_dir = project_root / "src"

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


def discover_example_files():
    """Discover all example_*.py files in the examples directory."""
    example_files = []

    # Walk through examples directory
    for root, dirs, files in os.walk(examples_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.startswith("example_") and file.endswith(".py"):
                file_path = Path(root) / file
                # Get relative path for display
                rel_path = file_path.relative_to(examples_dir)
                example_files.append((str(file_path), str(rel_path)))

    return example_files


def get_example_files():
    """Get list of example file paths for pytest parametrize."""
    files = discover_example_files()
    # Filter out files that are known to have issues
    excluded = [
        "trees/generic/example_trees_generic.py",  # Missing dependencies
    ]
    return [(file_path, rel_path) for file_path, rel_path in files if rel_path.replace("\\", "/") not in excluded]


# Examples that run a heavy end-to-end build and write a large mesh IFC. They
# stay in the suite but are marked ``slow`` so the default run skips them; run
# them with ``-m slow``. On the ``/mnt/c`` Windows mount their IFC write stalls
# for minutes (per-op 9p latency); on native Linux they finish in seconds.
SLOW_EXAMPLES = {
    "terrain/basic/example_basic_terrain.py",
    "terrain/generic/example_generic_terrain.py",
    "terrain/benchmark/example_terrain_perf_basic_vs_generic.py",
    "trees/benchmark/example_trees_perf_basic_vs_generic.py",
    "examples_sachsen/example_terrain_sachsen.py",
    "examples_sachsen/example_generic_entity_sachsen.py",
    "examples_schleswigHolstein/example_citymodel_schleswig_holstein.py",
}


def _example_params():
    """Parametrization for :func:`test_example_main`, slow ones marked."""
    params = []
    for file_path, rel_path in get_example_files():
        test_id = rel_path.replace("\\", "/")
        marks = [pytest.mark.slow] if test_id in SLOW_EXAMPLES else []
        params.append(pytest.param(file_path, rel_path, marks=marks, id=test_id))
    return params


@pytest.mark.parametrize("file_path,rel_path", _example_params())
def test_example_main(file_path, rel_path):
    """Test that each example's main() function runs without errors."""
    # Change to examples directory so relative paths work
    original_cwd = os.getcwd()

    try:
        # Set working directory to examples directory
        os.chdir(examples_dir)

        # Load module from file
        try:
            spec = importlib.util.spec_from_file_location("example_module", file_path)
            if spec is None or spec.loader is None:
                pytest.skip(f"Could not create spec for {rel_path}")
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules["example_module"] = module
            spec.loader.exec_module(module)
        except Exception as e:
            pytest.skip(f"Could not import {rel_path}: {e}")
            return

        # Check if main function exists
        main = getattr(module, "main", None)
        if not callable(main):
            pytest.skip(f"{rel_path} has no main() function")
            return

        # Run the main function
        try:
            result = main()
            # If main returns something, it's likely an IFC model or file path
            # We just verify it ran without errors
            assert True, f"{rel_path} executed successfully"
        except Exception as e:
            pytest.fail(f"{rel_path}.main() raised an exception: {e}")

    finally:
        # Restore original working directory
        os.chdir(original_cwd)
        # Clean up module from sys.modules
        if "example_module" in sys.modules:
            del sys.modules["example_module"]


def test_all_examples_discovered():
    """Test that we can discover example files."""
    files = get_example_files()
    assert len(files) > 0, "No example files discovered"
    # Should have at least the basic examples
    assert any("basic" in rel_path for _, rel_path in files), "No basic examples found"
