from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, model_validator

from .params_basepoint import BasepointParams
from .params_bbox import BoundingBoxParams
from .pydantic_georeferencing import check_point_in_crs, check_projected_epsg, check_source_epsg, check_vertical_epsg


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

    bbox: Optional[BoundingBoxParams] = Field(
        default=None,
        description=(
            "Bounding box in WGS84 longitude / latitude, independent of source_epsg and output_epsg "
            "(optional; if None, terrain uses full raster)"
        ),
    )
    containers: Optional[List[Container]] = None
    use_dgm_elevation: bool = Field(
        default=True,
        description=(
            "When true, download DGM GeoTIFF tiles and assign ground elevation to each tree. "
            "Tree model generation only; defaults to true. Set false to keep elevation 0."
        ),
    )
    source_epsg: Optional[int] = Field(
        default=None,
        description=(
            "EPSG code of the coordinate system the source data is in, e.g. 25832 for the Hamburg "
            "services, 4326 for WGS84 longitude / latitude or 5555 (only its horizontal part is "
            "used). Written to the IFC when no output_epsg is given, which then requires a 2D "
            "projected system in metres; otherwise output_epsg is required. WGS84 is converted to "
            "ETRS89 systems without a datum shift, so WGS84 positions can be off by about 1 m. "
            "Empty: the coordinates are written as they are, without any coordinate system in the IFC."
        ),
    )
    output_epsg: Optional[int] = Field(
        default=None,
        description=(
            "EPSG code the IFC should be in, e.g. 25832 (ETRS89 / UTM 32N) or 10285 (Gauß-Krüger "
            "Hamburg). The data is transformed from source_epsg into it, so the apps require "
            "source_epsg (the API sets it to the CRS it fetches the data in). Empty: no "
            "transformation. Heights are not transformed, see vertical_epsg."
        ),
    )
    vertical_epsg: Optional[int] = Field(
        default=None,
        description=(
            "EPSG code of the height system of the source data, e.g. 7837 (DHHN2016) or 5783 "
            "(DHHN92). Heights are not transformed; the code is written to the IFC as vertical "
            "datum and needs source_epsg. A compound source_epsg already names its heights (5555: "
            "DHHN92) and a different vertical_epsg is rejected. Empty: the vertical datum of a "
            "compound source_epsg, otherwise none."
        ),
    )
    basepoint: Optional[BasepointParams] = Field(
        default=None,
        description=(
            "Position of the Nullpunktobjekt in the CRS of the IFC (output_epsg, else source_epsg), "
            "e.g. the Nullpunkt of a model you already have, so both models share it. x / y are "
            "used as given, z is an absolute height (default 0). Empty: the lower-left corner of "
            "bbox at height 0."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "bbox": {"min_x": 9.9756, "min_y": 53.5522, "max_x": 9.9789, "max_y": 53.5536},
                "source_epsg": 25832,
                "output_epsg": 10285,
                "vertical_epsg": 7837,
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

    @model_validator(mode="after")
    def _check_epsg_codes(self) -> "RequestParams":
        if self.source_epsg is not None:
            check_source_epsg(self.source_epsg, self.output_epsg, self.bbox_as_wgs84_tuple)
        if self.output_epsg is not None:
            check_projected_epsg(self.output_epsg, self.bbox_as_wgs84_tuple)
        if self.vertical_epsg is not None:
            check_vertical_epsg(self.vertical_epsg, self.source_epsg)
        ifc_epsg = self.output_epsg or self.source_epsg
        if self.basepoint is not None and ifc_epsg is not None:
            check_point_in_crs(ifc_epsg, self.basepoint.x, self.basepoint.y)
        return self

    @property
    def basepoint_xyz(self) -> Optional[Tuple[float, float, float]]:
        """``basepoint`` as ``(x, y, z)`` in the CRS of the IFC, or ``None``."""
        return None if self.basepoint is None else self.basepoint.xyz

    @property
    def bbox_as_wgs84_tuple(self) -> Optional[Tuple[float, float, float, float]]:
        """Return ``bbox`` as ``(min_lon, min_lat, max_lon, max_lat)`` or ``None``.

        Convenience accessor shared by every app that needs to feed the
        bbox into a WGS84-only helper (parsers, basepoint fallback, ...).
        """
        if self.bbox is None:
            return None
        return (self.bbox.min_x, self.bbox.min_y, self.bbox.max_x, self.bbox.max_y)
