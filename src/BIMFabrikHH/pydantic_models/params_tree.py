from typing import Optional

from pydantic import BaseModel, Field

from .params_bbox import BoundingBoxParams


class ProjectInfos(BaseModel):
    project_name: Optional[str] = Field(default="IfcProjectName", description="Name of the project")
    site_name: Optional[str] = Field(default="SiteName", description="Name of the site")
    building_name: Optional[str] = Field(default="BuildingName", description="Name of the building")


class ModelParams(BaseModel):
    project_info: Optional[ProjectInfos] = Field(default=None, description="Project information")
    level_of_geom: int = Field(1, description="Level of geometry detail (1-4)", ge=1, le=4)


class RequestParams(BaseModel):
    """
    Request parameters for the API.
    """

    bbox: BoundingBoxParams = Field(..., description="Bounding box parameters")
    model_params: ModelParams = Field(..., description="Model parameters for the tree model")
