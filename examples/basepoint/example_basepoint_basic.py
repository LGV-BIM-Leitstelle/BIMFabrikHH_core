"""Basepoint via ``BasepointBasicApp`` (quad + extrusions). Geometry only: empty ``psets``.

Then ``python -m ifcopenshell.validate --rules`` on the written IFC.
"""

import subprocess
import sys
from pathlib import Path

from BIMFabrikHH_core.apps.basepoint.basic.app import BasepointBasicApp
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

_HERE = Path(__file__).resolve().parent
_OUT = _HERE / "example_basepoint_basic.ifc"


def main() -> None:
    BasepointBasicApp.build_ifc_from_basepoint_data(
        [{"position": (558_400.0, 5_927_500.0, 0.0), "size": 8.0, "psets": {}}],
        output_path=_OUT,
        coordinate_system=CoordinateSystemTemplates.gauss_kruger_hamburg(),
    )
    subprocess.run(
        [sys.executable, "-m", "ifcopenshell.validate", "--rules", str(_OUT)],
        check=True,
    )


if __name__ == "__main__":
    main()
