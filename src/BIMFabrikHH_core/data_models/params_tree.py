from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .params_bbox import BoundingBoxParams


class ProjectInfos(BaseModel):
    project_name: Optional[str] = Field(default="IfcProjectName", description="Name of the project")
    site_name: Optional[str] = Field(default="SiteName", description="Name of the site")
    building_name: Optional[str] = Field(default="BuildingName", description="Name of the building")


class ModelParams(BaseModel):
    project_info: Optional[ProjectInfos] = Field(default=None, description="Project information")
    level_of_geom: Optional[int] = Field(1, description="Level of geometry detail (1-4)", ge=1, le=4)


class Component(BaseModel):
    title: Optional[str] = None
    value: Optional[Any] = None


class Container(BaseModel):
    containerTitle: Optional[str] = None
    containerId: Optional[str] = None
    components: Optional[Dict[str, Component]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "containerTitle": "Tree Information",
                "containerId": "tree_data",
                "components": {
                    "species": {"title": "Tree Species", "value": "Oak"},
                    "height": {"title": "Tree Height", "value": 15.5},
                },
            }
        }
    }


class RequestParams(BaseModel):
    """
    Request parameters for the API.
    """

    bbox: BoundingBoxParams = Field(..., description="Bounding box parameters")
    containers: Optional[List[Container]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "bbox": {"min_x": 9.9756, "min_y": 53.5522, "max_x": 9.9789, "max_y": 53.5536},
                "containers": [
                    {
                        "containerTitle": "Tree Information",
                        "containerId": "tree_data",
                        "components": {
                            "species": {"title": "Tree Species", "value": "Oak"},
                            "height": {"title": "Tree Height", "value": 15.5},
                        },
                    }
                ],
            }
        }
    }
