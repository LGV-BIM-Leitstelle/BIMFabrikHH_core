#!/usr/bin/env python3
"""
Test script to run city model processing with timing analysis.
"""

from pathlib import Path

from BIMFabrikHH_core.apps.city.app import CityModularApp
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import Component, Container, RequestParams


def main():
    """Run city model processing with timing analysis."""

    print("=" * 60)
    print("CITY MODEL PROCESSING - TIMING ANALYSIS")
    print("=" * 60)

    # Check if XML files exist
    assets_path = PathConfig.ASSETS
    xml_files = [
        "LoD1_32_549_5935_1_HH.xml",
        "LoD1_32_549_5936_1_HH.xml",
        "LoD1_32_549_5937_1_HH.xml",
        "LoD1_32_549_5938_1_HH.xml",
    ]

    # Check which files exist
    available_files = []
    for xml_file in xml_files:
        file_path = assets_path / xml_file
        if file_path.exists():
            available_files.append(xml_file)
            print(f"✓ Found: {xml_file}")
        else:
            print(f"✗ Missing: {xml_file}")

    if not available_files:
        print("\n❌ No XML files found! Cannot run timing analysis.")
        print("Please ensure the XML files are in examples/assets/")
        return

    print(f"\n📁 Found {len(available_files)} XML files to process")

    # Create container
    container = Container(
        containerTitle="CityModel_Timing_Test",
        containerId="citymodel_timing",
        components={
            "description": Component(title="Description", value="Hamburg City Model Timing Test"),
            "type": Component(title="Model Type", value="LoD1 Building Models"),
            "test_type": Component(title="Test Type", value="Performance Timing Analysis"),
        },
    )

    # Create request parameters with a bounding box that should include the Hamburg data
    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.7400, min_y=53.5800, max_x=9.7600, max_y=53.5900),  # Hamburg area
        containers=[container],
    )

    print(f"\n🗺️  Bounding box: {request_body.bbox}")
    print(f"📦 Container: {container.containerTitle}")

    print("\n🚀 Starting city model processing...")
    print("=" * 60)

    try:
        # Use CityModularApp instead of process_gml_to_ifc
        app = CityModularApp(gml_files=available_files, folder_path=assets_path)

        # Step 1: Get raw data within bounding box
        raw_data = app.get_data_in_bbox(request_body.bbox)

        # Step 2: Process and clean data
        processed_data = app.process_data(raw_data)

        # Step 3: Create IFC
        result = app.create_ifc(processed_data, request_body)

        if result:
            print(f"\n✅ SUCCESS! IFC file created: {result}")
        else:
            print("\n❌ No IFC file was created.")

    except Exception as e:
        print(f"\n❌ ERROR during processing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
