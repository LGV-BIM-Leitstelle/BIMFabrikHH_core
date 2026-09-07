"""Same Hamburg LoD1 crop as ``example_generic_city_model.py``, via CityRustApp."""

from pathlib import Path

from BIMFabrikHH_core import (
    BoundingBoxParams,
    Component,
    Container,
    PathConfig,
    RequestParams,
)
from BIMFabrikHH_core.apps.city import CityRustApp
from BIMFabrikHH_core.config import get_logger, setup_logging

logger = get_logger()


def main() -> None:
    xml_files = [
        str(PathConfig.ASSETS / "LoD1_32_549_5935_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5936_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5937_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_549_5938_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_563_5934_1_HH.xml"),
        str(PathConfig.ASSETS / "LoD1_32_564_5934_1_HH.xml"),
    ]
    missing = [p for p in xml_files if not Path(p).is_file()]
    if missing:
        raise FileNotFoundError("LoD1 tiles not found:\n" + "\n".join(missing))

    request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9647, min_y=53.5531, max_x=9.9711, max_y=53.5564),
        containers=[
            Container(
                containerTitle="Citymodel_Container",
                containerId="citymodel_standard",
                components={
                    "description": Component(title="Description", value="Hamburg City Model Component"),
                    "type": Component(title="Model Type", value="LoD1 Building Models"),
                },
            )
        ],
    )

    output_file = Path(__file__).parent / "example_generic_rust_city_model.ifc"
    result = CityRustApp.from_gml_files(
        gml_files=xml_files,
        request_params=request_body,
        folder_path=Path(__file__).parent,
        mode="mesh",
        output_path=output_file,
    )
    if result:
        logger.info("OK %s", result, extra={"debug_category": "success"})
    else:
        logger.error("X Failed to create IFC file", extra={"debug_category": "error"})


if __name__ == "__main__":
    setup_logging()
    main()
