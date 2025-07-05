"""
Example: Tree Generic Optimised App with BasePoints
==================================================

This example demonstrates the new optimised app that uses:
- Modern dataclass-based geometry system
- Hybrid approach with both build() and as_product() methods
- Existing Pydantic models for property sets
- Composable geometry with Translate, Representation, and Product
- Automatic basepoint creation in the lower-left corner of tree bounding box

The app produces the same IFC output as the original generic app
but with a cleaner, more maintainable architecture and automatic basepoints.
"""

import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from BIMFabrikHH.apps.trees.optimised.app import TreeGenericApp


def main():
    """Main example function demonstrating the optimised tree app with automatic basepoints"""

    tree_data = [
        {
            "Easting": 558406.01,
            "Northing": 5927514.51,
            "kronendurchmesser": 58.0,
            "stammumfang": 1,
            "detail": 1,
            "segments": 8,
            "baumnummer": "100001",
            "gattung_deutsch": "Ahorn",
            "baumid": 1,
            "art_deutsch": "Spitz-Ahorn",
            "sorte_deutsch": "Spitz-Ahorn",
            "strasse": "Example Street",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Altona",
            "pflanzjahr": 1990,
        },
        {
            "Easting": 558553.52,
            "Northing": 5927499.96,
            "kronendurchmesser": 6.0,
            "stammumfang": 1.5,
            "detail": 2,
            "segments": 8,
            "height": 15.0,
            "baumnummer": "100002",
            "gattung_deutsch": "Eiche",
            "baumid": 2,
            "art_deutsch": "Stiel-Eiche",
            "sorte_deutsch": "Stiel-Eiche",
            "strasse": "Musterweg",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Bergedorf",
            "pflanzjahr": 1980,
        },
        {
            "Easting": 558501.93,
            "Northing": 5927581.88,
            "kronendurchmesser": 1,
            "stammumfang": 0.45,
            "baumnummer": "120220",
            "gattung_deutsch": "Linde",
            "baumid": 3,
            "art_deutsch": "Winter-Linde",
            "sorte_deutsch": "Winter-Linde",
            "strasse": "Musterweg",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Bramfeld",
            "pflanzjahr": 1985,
            "detail": 3,
            "segments": 8,
        },
        {
            "Easting": 558502.19,
            "Northing": 5927596.83,
            "kronendurchmesser": 2,
            "stammumfang": 0.45,
            "detail": 4,
            "segments": 8,
            "height": 17.0,
            "baumnummer": "100004",
            "gattung_deutsch": "Birke",
            "baumid": 4,
            "art_deutsch": "Hänge-Birke",
            "sorte_deutsch": "Hänge-Birke",
            "strasse": "Birch Street",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Harburg",
            "pflanzjahr": 1995,
        },
    ]

    print("=== Tree Generic Optimised App with Automatic BasePoints ===")
    print(f"Creating IFC model with {len(tree_data)} trees...")
    print("Basepoint will be created at the lower-left corner of the tree bounding box")

    # Generate trees and basepoint using the enhanced app
    output_path = Path(__file__).parent / "output_treecluster_optimised.ifc"
    TreeGenericApp.build_ifc_from_tree_data(tree_data, output_path)

    print(f"✅ IFC model created successfully: {output_path}")
    print("\n=== Example completed successfully! ===")
    print("The optimized app produces the same IFC output as the original")
    print("generic app but with a modern, composable architecture.")
    print("Plus basepoints for reference!")


if __name__ == "__main__":
    main()
