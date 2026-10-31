import math
import re
from functools import lru_cache
from typing import Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pyproj import CRS, Transformer
from pyproj.exceptions import CRSError

BboxWgs84 = Tuple[float, float, float, float]


@lru_cache(maxsize=64)
def _crs_from_epsg(epsg: int) -> CRS:
    try:
        return CRS.from_epsg(epsg)
    except CRSError as exc:
        raise ValueError(f"Unknown EPSG code: {epsg}") from exc


def horizontal_crs(epsg: int) -> CRS:
    """Horizontal part of ``epsg``: the CRS itself, or the first part of a compound CRS (e.g. 25832 of 5555)."""
    crs = _crs_from_epsg(epsg)
    return crs.sub_crs_list[0] if crs.is_compound else crs


def compound_vertical_epsg(epsg: int) -> Optional[int]:
    """EPSG code of the vertical part of a compound ``epsg`` (5555 → 5783), ``None`` otherwise."""
    crs = _crs_from_epsg(epsg)
    return crs.sub_crs_list[1].to_epsg() if crs.is_compound else None


def check_vertical_epsg(epsg: int, source_epsg: Optional[int] = None) -> None:
    """Raise ``ValueError`` unless ``epsg`` is a vertical CRS matching a compound ``source_epsg``.

    Heights are never transformed, so ``epsg`` only names the height system
    of the data, e.g. 7837 (DHHN2016) or 5783 (DHHN92).
    """
    crs = _crs_from_epsg(epsg)
    if crs.is_compound or not crs.is_vertical:
        raise ValueError(f"EPSG:{epsg} ({crs.name}) is not a vertical coordinate system")
    source_vertical = compound_vertical_epsg(source_epsg) if source_epsg is not None else None
    if source_vertical is not None and source_vertical != epsg:
        raise ValueError(
            f"vertical_epsg EPSG:{epsg} contradicts source_epsg EPSG:{source_epsg}, "
            f"whose heights are EPSG:{source_vertical}"
        )


def check_projected_epsg(epsg: int, bbox_wgs84: Optional[BboxWgs84] = None) -> None:
    """Raise ``ValueError`` unless ``epsg`` can be written to an IFC as its map CRS.

    It must be a 2D projected CRS with metre axes (``IfcProjectedCRS`` is
    horizontal only and IFC map coordinates are metres) and, when
    ``bbox_wgs84`` is given, its area of use must contain the bbox.
    """
    crs = _crs_from_epsg(epsg)
    if crs.is_compound or not crs.is_projected:
        raise ValueError(f"EPSG:{epsg} ({crs.name}) is not a 2D projected coordinate system")
    if any(axis.unit_name != "metre" for axis in crs.axis_info):
        raise ValueError(f"EPSG:{epsg} ({crs.name}) does not use metre axes")
    area = crs.area_of_use
    if bbox_wgs84 is not None and area is not None:
        min_lon, min_lat, max_lon, max_lat = bbox_wgs84
        if min_lon < area.west or min_lat < area.south or max_lon > area.east or max_lat > area.north:
            raise ValueError(f"The bbox lies outside the area of use of EPSG:{epsg} ({area.name})")


def check_point_in_crs(epsg: int, x: float, y: float) -> None:
    """Raise ``ValueError`` unless ``(x, y)`` lies in the area of use of ``epsg``.

    Catches swapped axes or degrees instead of metres; whether it is the right
    point is up to the caller.
    """
    horizontal = horizontal_crs(epsg)
    area = horizontal.area_of_use
    if area is None:
        return
    lon, lat = Transformer.from_crs(horizontal, _crs_from_epsg(4326), always_xy=True).transform(x, y)
    if not (math.isfinite(lon) and math.isfinite(lat)) or not (
        area.west <= lon <= area.east and area.south <= lat <= area.north
    ):
        raise ValueError(f"({x}, {y}) lies outside the area of use of EPSG:{epsg} ({area.name})")


def check_source_epsg(
    epsg: int,
    output_epsg: Optional[int] = None,
    bbox_wgs84: Optional[BboxWgs84] = None,
) -> None:
    """Raise ``ValueError`` unless data in ``epsg`` can be written with ``output_epsg``.

    The source may be projected, geographic (e.g. 4326) or compound (e.g.
    5555, only its horizontal part is used); heights are never transformed.
    Without ``output_epsg`` the source itself becomes the IFC map CRS and must
    pass :func:`check_projected_epsg`.
    """
    horizontal = horizontal_crs(epsg)
    if not (horizontal.is_projected or horizontal.is_geographic):
        raise ValueError(f"EPSG:{epsg} ({horizontal.name}) has no horizontal coordinate system to transform from")
    if output_epsg is None:
        try:
            check_projected_epsg(epsg, bbox_wgs84)
        except ValueError as exc:
            raise ValueError(f"{exc}; set output_epsg to write the data in a projected coordinate system") from exc


class CoordinateOperation(BaseModel):
    """
    Transformation parameters for local to projected CRS.
    """

    eastings: float = Field(
        0.0,
        serialization_alias="Eastings",
        description="Projected easting of the local engineering origin",
    )
    northings: float = Field(
        0.0,
        serialization_alias="Northings",
        description="Projected northing of the local engineering origin",
    )
    orthogonal_height: float = Field(
        0.0,
        serialization_alias="OrthogonalHeight",
        description="Projected height of the local engineering origin",
    )
    x_axis_abscissa: float = Field(
        1.0, serialization_alias="XAxisAbscissa", description="X-axis abscissa (cos of rotation angle)"
    )
    x_axis_ordinate: float = Field(
        0.0, serialization_alias="XAxisOrdinate", description="X-axis ordinate (sin of rotation angle)"
    )
    scale: float = Field(1.0, serialization_alias="Scale", description="Scale factor")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    @model_validator(mode="after")
    def validate_transformation(self) -> "CoordinateOperation":
        values = (
            self.eastings,
            self.northings,
            self.orthogonal_height,
            self.x_axis_abscissa,
            self.x_axis_ordinate,
            self.scale,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("coordinate operation values must be finite")
        if self.x_axis_abscissa == 0.0 and self.x_axis_ordinate == 0.0:
            raise ValueError("x-axis direction cannot be the zero vector")
        if self.scale <= 0.0:
            raise ValueError("scale must be greater than zero")
        return self


class CoordinateSystem(BaseModel):
    """
    Simple coordinate system model for IFC4 georeferencing.
    Only requires fields that ifcopenshell actually needs.
    Defaults to EPSG:25832 (ETRS89 / UTM zone 32N) values.
    """

    # Required fields for ifcopenshell IfcProjectedCRS
    name: str = Field(
        ..., serialization_alias="Name", description="Name of the coordinate system (e.g., 'WGS84', 'EPSG:25832')"
    )
    geodetic_datum: str = Field(
        ..., serialization_alias="GeodeticDatum", description="Geodetic datum (e.g., 'WGS84', 'ETRS89')"
    )

    # Optional fields with EPSG:25832 defaults
    description: Optional[str] = Field(
        "ETRS89 / UTM zone 32N", serialization_alias="Description", description="Description of the coordinate system"
    )
    vertical_datum: Optional[str] = Field(
        "EPSG:7837",
        serialization_alias="VerticalDatum",
        description="Vertical datum as EPSG code, e.g. 'EPSG:7837' (DHHN2016)",
    )
    map_projection: Optional[str] = Field(
        "Transverse Mercator", serialization_alias="MapProjection", description="Map projection type"
    )
    map_zone: Optional[str] = Field("32", serialization_alias="MapZone", description="Map zone identifier")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    @classmethod
    def from_epsg(cls, epsg: int, vertical_epsg: Optional[int] = None) -> "CoordinateSystem":
        """Build the IFC projected CRS for ``epsg`` from the pyproj definition.

        The vertical datum is ``"EPSG:<vertical_epsg>"``, or empty when the
        height system is unknown.
        """
        if vertical_epsg is not None:
            check_vertical_epsg(vertical_epsg)
        check_projected_epsg(epsg)
        crs = _crs_from_epsg(epsg)
        operation = crs.coordinate_operation
        zone = re.search(r"zone (\d+)", crs.name)
        return cls(
            name=f"EPSG:{epsg}",
            description=crs.name,
            geodetic_datum=crs.geodetic_crs.name,
            vertical_datum=f"EPSG:{vertical_epsg}" if vertical_epsg is not None else None,
            map_projection=operation.method_name if operation is not None else None,
            map_zone=zone.group(1) if zone else None,
        )


class CoordinateSystemTemplates:
    """
    Predefined coordinate system templates for common use cases.
    """

    @staticmethod
    def epsg_25832() -> CoordinateSystem:
        """EPSG:25832 - ETRS89 / UTM zone 32N, heights DHHN2016."""
        return CoordinateSystem.from_epsg(25832, vertical_epsg=7837)

    @staticmethod
    def epsg_25833() -> CoordinateSystem:
        """EPSG:25833 - ETRS89 / UTM zone 33N (used in Sachsen and eastern Germany), heights DHHN2016."""
        return CoordinateSystem.from_epsg(25833, vertical_epsg=7837)

    @staticmethod
    def gauss_kruger_hamburg() -> CoordinateSystem:
        """EPSG:10285 - ETRS89/DREF91/2016 / 3-degree Gauss-Kruger zone 3 (Hamburg), heights DHHN2016."""
        return CoordinateSystem.from_epsg(10285, vertical_epsg=7837)

    @staticmethod
    def get_template(template_name: Literal["epsg_25832", "epsg_25833", "gauss_kruger_hamburg"]) -> CoordinateSystem:
        """
        Get a predefined coordinate system template.

        Args:
            template_name: Name of the template to retrieve

        Returns:
            CoordinateSystem: The requested coordinate system template
        """
        templates = {
            "epsg_25832": CoordinateSystemTemplates.epsg_25832,
            "epsg_25833": CoordinateSystemTemplates.epsg_25833,
            "gauss_kruger_hamburg": CoordinateSystemTemplates.gauss_kruger_hamburg,
        }

        if template_name not in templates:
            raise ValueError(f"Unknown template: {template_name}. Available templates: {list(templates.keys())}")

        return templates[template_name]()

    @staticmethod
    def get_default_coordinate_operation() -> CoordinateOperation:
        """
        Get a default identity coordinate operation (no transformation).

        Returns:
            CoordinateOperation: Default identity transformation
        """
        return CoordinateOperation(
            eastings=0.0,
            northings=0.0,
            orthogonal_height=0.0,
            x_axis_abscissa=1.0,  # cos(0°) = 1.0 (identity rotation)
            x_axis_ordinate=0.0,  # sin(0°) = 0.0 (identity rotation)
            scale=1.0,
        )
