"""Generic city-model example (ifcfactory pipeline).

Parses the same Hamburg LoD1 tiles as the basic example, cropped by a
WGS84 bbox, and writes a single IFC via :class:`CityGenericApp` —
``ifcfactory.BIMFactoryElement`` / ``MeshRepresentation`` / ``Style``
instead of raw ``ifcopenshell.api`` calls.
"""

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core import (
    BoundingBoxParams,
    Component,
    Container,
    PathConfig,
    RequestParams,
)
from BIMFabrikHH_core.apps.city import CityGenericApp
from BIMFabrikHH_core.config import get_logger, setup_logging

logger = get_logger()


def main() -> None:
    """Process Hamburg LoD1 tiles into a single IFC city model via ifcfactory."""
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
        bbox=BoundingBoxParams(min_x=9.9647, min_y=53.5531, max_x=9.9711, max_y=53.5564),
        containers=[container],
    )

    output_file = citymodel_folder / "example_generic_city_model.ifc"
    result = CityGenericApp.from_gml_files(
        gml_files=xml_files,
        request_params=request_body,
        folder_path=citymodel_folder,
        output_path=output_file,
    )

    if result:
        logger.info(
            f"OK Successfully created {result.name}\n{result.parent}",
            extra={"debug_category": "success"},
        )
        subprocess.run(
            [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(result)],
            check=True,
        )
    else:
        logger.error("X Failed to create IFC file", extra={"debug_category": "error"})


if __name__ == "__main__":
    setup_logging()
    main()
