"""Basepoint via ``ProjectBasePointNorthMesh`` (pyramid mesh + overlays). Geometry only: ``psets=[]``.

Then ``python -m ifcopenshell.validate --rules`` on the written IFC.
"""

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core.config import setup_logging
from BIMFabrikHH_core.core.geometry import ProjectBasePointNorthMesh
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateSystemTemplates,
)

_HERE = Path(__file__).resolve().parent
_OUT = _HERE / "example_basepoint_generic.ifc"


def main() -> None:
    b = IfcModelBuilder()
    b.build_project(
        project_name="BasepointGeneric",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Site",
        building_name="Building",
    )
    site = b.model.by_type("IfcSite")[0]
    ProjectBasePointNorthMesh(size=8.0, psets=[], container=site).build(b.model)
    b.save_ifc_to_output(_OUT.name, output_path=_OUT)
    subprocess.run(
        [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(_OUT)],
        check=True,
    )


if __name__ == "__main__":
    setup_logging()
    main()
