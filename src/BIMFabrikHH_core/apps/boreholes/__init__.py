"""Baugrundaufschluss (borehole) apps.

Input is a Hamburg WFS ``BoreholeML 3.0`` ``GetFeature`` response. Fetching
happens in the caller (the API), this package only parses the response into
:class:`BoreholeRecord` objects and writes IFC.
"""

from BIMFabrikHH_core.data_models.boreholes import (
    BoreholeLayer,
    BoreholeRecord,
    collect_borehole_psets,
)

from .generic.app import BoreholesGenericApp
from .processing import (
    BOREHOLE_PORTAL_SID,
    BOREHOLE_PORTAL_URL,
    build_borehole_hyperlink,
    load_borehole_records,
    map_color_code,
    map_hauptgemengteil,
    map_nebengemengteil,
    map_soil_symbol,
    map_stratigraphy,
    records_from_boreholeml,
    visual_color_for_hauptgemengteil,
)

__all__ = [
    "BOREHOLE_PORTAL_SID",
    "BOREHOLE_PORTAL_URL",
    "BoreholesGenericApp",
    "BoreholeLayer",
    "BoreholeRecord",
    "build_borehole_hyperlink",
    "collect_borehole_psets",
    "load_borehole_records",
    "map_color_code",
    "map_hauptgemengteil",
    "map_nebengemengteil",
    "map_soil_symbol",
    "map_stratigraphy",
    "records_from_boreholeml",
    "visual_color_for_hauptgemengteil",
]
