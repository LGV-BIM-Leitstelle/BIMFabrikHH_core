from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class CoordinateOperation(BaseModel):
    """
    Transformation parameters for local to projected CRS.
    """

    eastings: float = Field(0.0, serialization_alias="Eastings", description="False easting in meters")
    northings: float = Field(0.0, serialization_alias="Northings", description="False northing in meters")
    orthogonal_height: float = Field(
        0.0, serialization_alias="OrthogonalHeight", description="Orthogonal height in meters"
    )
    x_axis_abscissa: float = Field(
        1.0, serialization_alias="XAxisAbscissa", description="X-axis abscissa (cos of rotation angle)"
    )
    x_axis_ordinate: float = Field(
        0.0, serialization_alias="XAxisOrdinate", description="X-axis ordinate (sin of rotation angle)"
    )
    scale: float = Field(1.0, serialization_alias="Scale", description="Scale factor")


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
        "DHHN2016", serialization_alias="VerticalDatum", description="Vertical datum (e.g., 'DHHN2016')"
    )
    map_projection: Optional[str] = Field(
        "Transverse Mercator", serialization_alias="MapProjection", description="Map projection type"
    )
    map_zone: Optional[str] = Field("32", serialization_alias="MapZone", description="Map zone identifier")

    model_config = ConfigDict(validate_assignment=True, extra="forbid")


class CoordinateSystemTemplates:
    """
    Predefined coordinate system templates for common use cases.
    """

    @staticmethod
    def epsg_25832() -> CoordinateSystem:
        """EPSG:25832 - ETRS89 / UTM zone 32N."""
        return CoordinateSystem(
            name="EPSG:25832",
            description="ETRS89 / UTM zone 32N",
            geodetic_datum="ETRS89",
            vertical_datum="DHHN2016",
            map_projection="Transverse Mercator",
            map_zone="32",
        )

    @staticmethod
    def gauss_kruger_hamburg() -> CoordinateSystem:
        """Gauß-Krüger coordinate system for Hamburg area."""
        return CoordinateSystem(
            name="Gauß-Krüger Hamburg",
            description="Gauß-Krüger coordinate system for Hamburg metropolitan area",
            geodetic_datum="Potsdam Datum",
            vertical_datum="DHHN2016",
            map_projection="Transverse Mercator",
            map_zone="3",
        )

    @staticmethod
    def get_template(template_name: Literal["epsg_25832", "gauss_kruger_hamburg"]) -> CoordinateSystem:
        """
        Get a predefined coordinate system template.

        Args:
            template_name: Name of the template to retrieve

        Returns:
            CoordinateSystem: The requested coordinate system template
        """
        templates = {
            "epsg_25832": CoordinateSystemTemplates.epsg_25832,
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
