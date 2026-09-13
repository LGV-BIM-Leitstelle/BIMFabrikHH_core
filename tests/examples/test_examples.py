"""Discover example scripts. Do not execute them.

``example_*.py`` files are demos (full GeoTIFF / CityGML → IFC). They are
not the unit suite: running ``main()`` writes large IFCs onto ``/mnt/c``
and several of them call ``ifcopenshell.validate --rules``. Use
``tests/test_app_*.py`` for that coverage, and run an example by invoking
the script itself.
"""

import os
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent.parent
examples_dir = project_root / "examples"


def discover_example_files():
    """Discover all example_*.py files in the examples directory."""
    example_files = []

    for root, dirs, files in os.walk(examples_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]

        for file in files:
            if file.startswith("example_") and file.endswith(".py"):
                file_path = Path(root) / file
                rel_path = file_path.relative_to(examples_dir)
                example_files.append((str(file_path), str(rel_path)))

    return example_files


# Benchmarks compare writers and run ``ifcopenshell.validate --rules``.
# They are not collected as tests; run them as scripts when you want a bench.
PERF_EXAMPLES = {
    "terrain/benchmark/example_terrain_perf_basic_vs_generic.py",
    "trees/benchmark/example_trees_perf_basic_vs_generic.py",
}


def get_example_files():
    """Example scripts that count as demos (excludes the two perf benches)."""
    excluded = {
        "trees/generic/example_trees_generic.py",  # Missing dependencies
        *PERF_EXAMPLES,
    }
    return [
        (file_path, rel_path)
        for file_path, rel_path in discover_example_files()
        if rel_path.replace("\\", "/") not in excluded
    ]


def test_all_examples_discovered():
    """Test that we can discover example files."""
    files = get_example_files()
    assert len(files) > 0, "No example files discovered"
    assert any("basic" in rel_path for _, rel_path in files), "No basic examples found"
    discovered = {rel_path.replace("\\", "/") for _, rel_path in discover_example_files()}
    assert PERF_EXAMPLES <= discovered, "perf example scripts should still exist on disk"
