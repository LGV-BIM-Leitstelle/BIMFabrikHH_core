import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, PathConfig, RequestParams
from BIMFabrikHH_core.apps.city.app import CityModularApp
from BIMFabrikHH_core.config import get_logger

logger = get_logger()


def main():
    """Process citymodel files to create IFC."""
    citymodel_folder = Path(__file__).parent
    xml_files = [
        str(PathConfig.ASSETS / "LoD1_32_549_5935_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5936_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5937_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5938_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_563_5934_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_564_5934_1_HH.xml"),
    ]

    container = Container(
        containerTitle="Citymodel_Container",
        containerId="citymodel_standard",
        components={
            "description": Component(title="Description", value="Hamburg City Model Component"),
            "type": Component(title="Model Type", value="LoD1 Building Models"),
        },
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9647, min_y=53.5531, max_x=9.9711, max_y=53.5564), containers=[container]
    )

    # Use CityModularApp instead of process_gml_to_ifc
    app = CityModularApp(gml_files=xml_files, folder_path=citymodel_folder)

    # Step 1: Get raw data within bounding box
    raw_data = app.get_data_in_bbox(request_body.bbox)

    # Step 2: Process and clean data
    processed_data = app.process_data(raw_data)

    # Step 3: Create IFC
    result = app.create_ifc(processed_data, request_body)

    if result:
        logger.info(f"✓ Successfully created {result.name}\n{result.parent}", extra={"debug_category": "success"})
        subprocess.run(
            [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(result)],
            check=True,
        )
    else:
        logger.error("✗ Failed to create IFC file", extra={"debug_category": "error"})


if __name__ == "__main__":
    main()
