from typing import Annotated

from pydantic import BaseModel, Field


class BoundingBoxParams(BaseModel):
    min_x: Annotated[float, Field(ge=8.421, le=10.326)] = Field(
        9.9733, description="Minimum longitude of the bounding box"
    )
    min_y: Annotated[float, Field(ge=53.395, le=53.964)] = Field(
        53.5544, description="Minimum latitude of the bounding box"
    )
    max_x: Annotated[float, Field(ge=8.421, le=10.326)] = Field(
        9.9756, description="Maximum longitude of the bounding box"
    )
    max_y: Annotated[float, Field(ge=53.395, le=53.964)] = Field(
        53.5556, description="Maximum latitude of the bounding box"
    )
