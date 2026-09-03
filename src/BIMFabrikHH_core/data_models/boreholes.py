"""Baugrundaufschluss (borehole) input records.

Parsed from Hamburg WFS ``BoreholeML 3.0`` ``GetFeature`` responses
(``bml:Borehole``) by
:mod:`BIMFabrikHH_core.apps.boreholes.processing`. One
:class:`BoreholeRecord` holds the borehole head data plus its ordered
:class:`BoreholeLayer` list, because the layer cylinders are stacked per
borehole.

Coordinates are **EPSG:25832** ``(easting, northing)`` in metres and heights
are metres NHN. The WFS delivers ``EPSG:5555``, whose horizontal part is
EPSG:25832, so the values are used as they arrive (see
:func:`~BIMFabrikHH_core.apps.boreholes.processing._borehole_position`).

Like :class:`TreeRecord`, both levels carry IFC pset templates under
``psets``, filled while parsing.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class BoreholeLayer(BaseModel):
    """One ``bml:Interval`` of a borehole: a single soil layer."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    layer_id: str = Field(description="Stable id ``<borehole id>_<index>``")
    from_depth: float = Field(description="Upper layer boundary in m below Ansatzpunkt")
    to_depth: float = Field(description="Lower layer boundary in m below Ansatzpunkt")
    upper_height: float = Field(description="Upper layer boundary in m NHN")
    lower_height: float = Field(description="Lower layer boundary in m NHN")
    thickness: float = Field(description="Layer thickness in m (cylinder height)")

    hauptgemengteil: str = Field(default="", description="Main soil code, e.g. ``mS``")
    nebengemengteil: str = Field(default="", description="Secondary soil codes, comma separated")
    rock_name_text: str = Field(default="", description="German plain text from ``bml:rockNameText``")
    stratigraphie: str = Field(default="", description="``chronoStratigraphy`` code")
    genese: str = Field(default="", description="``geoGenesis`` / ``genesis`` code")
    farbe: str = Field(default="", description="``rockColor`` code")
    kalkgehalt: str = Field(default="", description="``carbonateContent`` code")
    konsistenz: str = Field(default="", description="``consistency`` code")

    visual_rgb: tuple[int, int, int] = Field(
        default=(254, 254, 254),
        description="DIN 4023 display colour derived from ``hauptgemengteil`` (0-255)",
    )
    din_color_name: str = Field(default="weiß", description="German name of ``visual_rgb``")

    psets: Dict[str, BaseModel] = Field(default_factory=dict)


class BoreholeRecord(BaseModel):
    """One ``bml:Borehole`` feature with its ordered layers."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")

    borehole_id: str = Field(description="``bml:id``, e.g. ``BDHH_6434B1``")
    aufschlussbezeichnung: str = Field(default="", description="``bml:fullName`` (fallback ``shortName``)")
    easting: float = Field(description="EPSG:25832 easting in m")
    northing: float = Field(description="EPSG:25832 northing in m")
    ansatzhoehe_nn: float = Field(description="Ground level at the Ansatzpunkt in m NHN")
    endteufe: Optional[float] = Field(default=None, description="``bml:totalLength`` in m")
    bohrdatum: str = Field(default="", description="``bml:drillingDate`` (ISO date)")
    bohrvorgang: str = Field(default="", description="``bml:drillingMethod`` code")
    projekt: str = Field(default="", description="``bml:project``")

    layers: List[BoreholeLayer] = Field(default_factory=list)
    psets: Dict[str, BaseModel] = Field(default_factory=dict)


def collect_borehole_psets(
    record: BoreholeRecord,
    layer: BoreholeLayer,
    *,
    include_property_sets: bool = True,
) -> List[BaseModel]:
    """Merge the borehole-level and layer-level pset templates for one cylinder.

    Args:
        record: The borehole the layer belongs to.
        layer: The layer being turned into a cylinder.
        include_property_sets: When ``False`` an empty list is returned.

    Returns:
        Pydantic pset templates, borehole-level first (cf. ``collect_pydantic_psets``).
    """
    if not include_property_sets:
        return []

    out: List[BaseModel] = []
    for source, scope in ((record.psets, record.borehole_id), (layer.psets, layer.layer_id)):
        for pset_name, value in source.items():
            if isinstance(value, BaseModel):
                out.append(value)
            else:
                logger.warning(
                    "Borehole %s: pset '%s' is not a pydantic BaseModel (got %s); skipped.",
                    scope,
                    pset_name,
                    type(value).__name__,
                )
    return out


__all__ = [
    "BoreholeLayer",
    "BoreholeRecord",
    "collect_borehole_psets",
]
