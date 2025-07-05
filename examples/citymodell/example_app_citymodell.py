from pathlib import Path

from BIMFabrikHH import BoundingBoxParams, Component, Container, PathConfig, RequestParams, process_gml_to_ifc
from BIMFabrikHH.logging_config import get_logger

logger = get_logger()


def main():
    """Process citymodel files to create IFC."""
    citymodel_folder = Path(__file__).parent
    xml_files = [
        "../assets/LoD1_32_549_5935_1_HH.xml",
        "../assets/LoD1_32_549_5936_1_HH.xml",
        "../assets/LoD1_32_549_5937_1_HH.xml",
        "../assets/LoD1_32_549_5938_1_HH.xml",
    ]
    output_file = PathConfig.OUTPUT / "example_citymodell.ifc"

    container = Container(
        containerTitle="Citymodel_Container",
        containerId="citymodel_standard",
        components={
            "description": Component(title="Description", value="Hamburg City Model Component"),
            "type": Component(title="Model Type", value="LoD1 Building Models"),
        },
    )

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.7500, min_y=53.5813, max_x=9.7483, max_y=53.5856), containers=[container]
    )

    result = process_gml_to_ifc(xml_files, request_body, folder_path=citymodel_folder, move_to_origin=True)

    if result:
        logger.info(f"✓ Successfully created {result.name}\n{result.parent}", extra={"debug_category": "success"})
    else:
        logger.error("✗ Failed to create IFC file", extra={"debug_category": "error"})


if __name__ == "__main__":
    main()
