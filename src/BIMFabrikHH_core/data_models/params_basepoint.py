from typing import Tuple

from pydantic import BaseModel, Field


class BasepointParams(BaseModel):
    """Position of the Nullpunktobjekt, e.g. taken from a model the user already has.

    ``x`` / ``y`` are in the CRS of the IFC (``output_epsg``, else
    ``source_epsg``), ``z`` is an absolute height in its height system. The
    values are used as given; only their area of use is checked.
    """

    x: float = Field(allow_inf_nan=False, description="Easting / x in the CRS of the IFC")
    y: float = Field(allow_inf_nan=False, description="Northing / y in the CRS of the IFC")
    z: float = Field(default=0.0, allow_inf_nan=False, description="Absolute height; 0 when not given")

    model_config = {"json_schema_extra": {"example": {"x": 565012.0, "y": 5933559.0, "z": 12.5}}}

    @property
    def xyz(self) -> Tuple[float, float, float]:
        return self.x, self.y, self.z
