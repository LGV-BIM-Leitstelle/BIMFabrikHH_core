from pydantic import BaseModel
from typing import Optional


class GeoreferencingData(BaseModel):
    Eastings: Optional[float] = None
    Northings: Optional[float] = None
    OrthogonalHeight: Optional[float] = None
    XAxisAbscissa: Optional[float] = None
    XAxisOrdinate: Optional[float] = None
    Scale: Optional[float] = None
    # SourceCRS: Optional[str]
    # TargetCRS: Optional[str]


class ProjectedCRSData(BaseModel):
    Name: Optional[str] = None
    Description: Optional[str] = None
    GeodeticDatum: Optional[str] = None
    VerticalDatum: Optional[str] = None
    MapProjection: Optional[str] = None
    MapZone: Optional[str] = None
    MapUnit: Optional[str] = None


class IFCGeoReferencing(BaseModel):
    IfcMapConversion: Optional[GeoreferencingData]
    IfcProjectedCRS: Optional[ProjectedCRSData]
