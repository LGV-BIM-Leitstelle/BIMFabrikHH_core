from pydantic import BaseModel, Field

from ..pydantic_models.params_bbox import BoundingBoxParams


class ModelParams(BaseModel):
    bbox: BoundingBoxParams = Field(..., description="Bounding box parameters")
    level_of_geom: int = Field(1, description="Level of geometry detail (1-4)", ge=1, le=4)
    project_name: str = Field(default="Projektname", description="Name of the project")
    site_name: str = Field(default="SiteName", description="Name of the site")
