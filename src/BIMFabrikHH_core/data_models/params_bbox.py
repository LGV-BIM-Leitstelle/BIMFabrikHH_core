from typing import Annotated

from pydantic import BaseModel, Field


class BoundingBoxParams(BaseModel):
    """
    Bounding box parameters for geospatial data queries.

    This model defines the boundaries of a geographic area using WGS84 coordinates
    (longitude/latitude). The coordinates are constrained to the Hamburg area.

    Attributes:
        min_x: Minimum longitude (west boundary) of the bounding box.
        min_y: Minimum latitude (south boundary) of the bounding box.
        max_x: Maximum longitude (east boundary) of the bounding box.
        max_y: Maximum latitude (north boundary) of the bounding box.
    """

    min_x: Annotated[float, Field(ge=8.421, le=10.326)] = Field(
        9.9756, description="Minimum longitude of the bounding box"
    )
    min_y: Annotated[float, Field(ge=53.395, le=53.964)] = Field(
        53.5522, description="Minimum latitude of the bounding box"
    )
    max_x: Annotated[float, Field(ge=8.421, le=10.326)] = Field(
        9.9789, description="Maximum longitude of the bounding box"
    )
    max_y: Annotated[float, Field(ge=53.395, le=53.964)] = Field(
        53.5536, description="Maximum latitude of the bounding box"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "min_x": 9.9756,
                "min_y": 53.5522,
                "max_x": 9.9789,
                "max_y": 53.5536,
                "description": "Small area in Hamburg city center (WGS84 coordinates)",
            }
        }
    }
