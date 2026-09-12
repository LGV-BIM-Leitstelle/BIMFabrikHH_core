"""Terrain-specific IFC-adjacent helpers.

Shared by :class:`TerrainBasicApp` and :class:`TerrainGenericApp`. Pure
mesh / coordinate math lives in
:mod:`BIMFabrikHH_core.apps.terrain.processing`; this module only
covers terrain-specific glue code between a :class:`TerrainMesh` and an
IFC model (default psets).

The basepoint-placement helper lives in
:func:`BIMFabrikHH_core.core.geometry.place_basepoint`. Request-bbox
reprojection to EPSG:25832 is
:func:`BIMFabrikHH_core.core.georeferencing.bbox_request_params_to_epsg25832`.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel

from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import Pset_Objektinformation_DGM
from BIMFabrikHH_core.data_models.streets import PARCELS_LABEL

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

DEFAULT_TERRAIN_RGB: RgbTuple = (220, 40, 40)
DEFAULT_TERRAIN_LAYER: str = "_BIM_DGM_Gelaende"

_BEGLEIT_RGB: RgbTuple = (175, 175, 180)
_WATER_RGB: RgbTuple = (120, 170, 210)
# Land-use types share a magenta ramp (light → dark). Grünfläche is park green.
TERRAIN_NUTZART_RGB: Dict[str, RgbTuple] = {
    "DGM": (220, 40, 40),
    "Strassenverkehr": (110, 110, 115),
    "Strassenverkehr|Fahrbahn": (55, 55, 60),
    "Strassenverkehr|Begleitfläche Straßenverkehr": _BEGLEIT_RGB,
    "Strassenverkehr|Busbahnhof": _BEGLEIT_RGB,
    "Strassenverkehr|Fußgängerzone": _BEGLEIT_RGB,
    "Strassenverkehr|Parkplatz": _BEGLEIT_RGB,
    "Weg": (230, 120, 40),
    "Bahnverkehr": (90, 75, 75),
    "Platz": (236, 186, 220),
    "Wohnbauflaeche": (228, 168, 210),
    "Flaeche Gemischter Nutzung": (220, 154, 202),
    "Industrie Und Gewerbeflaeche": (212, 140, 194),
    "Flaeche Besonderer Funktionaler Praegung": (204, 128, 186),
    "Sport Freizeit Und Erholungsflaeche": (36, 150, 52),
    "Fliessgewaesser": _WATER_RGB,
    "Stehendes Gewaesser": _WATER_RGB,
    "Hafenbecken": _WATER_RGB,
    "Meer": _WATER_RGB,
    "Schiffsverkehr": _WATER_RGB,
    "Unland Vegetationslose Flaeche": (242, 241, 239),
    PARCELS_LABEL: (166, 140, 100),
}
TERRAIN_NUTZART_LAYER: Dict[str, str] = {
    "Strassenverkehr": "_BIM_DGM_Strassenverkehr",
    "Strassenverkehr|Fahrbahn": "_BIM_DGM_Fahrbahn",
    "Strassenverkehr|Begleitfläche Straßenverkehr": "_BIM_DGM_Begleitflaeche",
    "Strassenverkehr|Busbahnhof": "_BIM_DGM_Begleitflaeche",
    "Strassenverkehr|Fußgängerzone": "_BIM_DGM_Begleitflaeche",
    "Strassenverkehr|Parkplatz": "_BIM_DGM_Begleitflaeche",
    "Weg": "_BIM_DGM_Weg",
    "Bahnverkehr": "_BIM_DGM_Bahnverkehr",
    "Platz": "_BIM_DGM_Platz",
    "Wohnbauflaeche": "_BIM_DGM_Wohnbau",
    "Industrie Und Gewerbeflaeche": "_BIM_DGM_Gewerbe",
    "Flaeche Gemischter Nutzung": "_BIM_DGM_GemischteNutzung",
    "Flaeche Besonderer Funktionaler Praegung": "_BIM_DGM_FunktionalePraegung",
    "Sport Freizeit Und Erholungsflaeche": "_BIM_DGM_Freizeit",
    "Fliessgewaesser": "_BIM_DGM_Fliessgewaesser",
    "Stehendes Gewaesser": "_BIM_DGM_StehendesGewaesser",
    "Hafenbecken": "_BIM_DGM_Hafenbecken",
    "Meer": "_BIM_DGM_Meer",
    "Schiffsverkehr": "_BIM_DGM_Schiffsverkehr",
    "Unland Vegetationslose Flaeche": "_BIM_DGM_Unland",
    PARCELS_LABEL: "_BIM_DGM_Parcels",
}


def safe_label(label: str) -> str:
    """Filesystem/identifier-safe form of a Nutzart label."""
    return label.replace("|", "_").replace(" ", "_")[:80]


def color_for_label(label: str, fallback: RgbTuple) -> RgbTuple:
    """RGB for a land-use ``label`` (exact key, then base type, then fallback)."""
    if label in TERRAIN_NUTZART_RGB:
        return TERRAIN_NUTZART_RGB[label]
    base = label.split("|", 1)[0]
    return TERRAIN_NUTZART_RGB.get(base, fallback)


def terrain_part_style(
    label: str,
    *,
    color: RgbTuple,
    cad_layer: str,
    name: str,
) -> Tuple[str, RgbTuple, str]:
    """Shared ``(part_name, color, cad_layer)`` for one land-use part.

    Both :class:`TerrainGenericApp` and :class:`TerrainRustApp` call this so a
    Fahrbahn (etc.) gets the same colour, layer and element name regardless of
    the IFC writer. ``color`` / ``cad_layer`` are the fallbacks used for the
    leftover ``DGM`` part and any unknown label.
    """
    part_color = color_for_label(label, color)
    part_layer = TERRAIN_NUTZART_LAYER.get(
        label, cad_layer if label == "DGM" else f"_BIM_DGM_{safe_label(label)}"
    )
    part_name = name if label == "DGM" else f"{name}_{safe_label(label)}"
    return part_name, part_color, part_layer


def default_terrain_psets() -> List[BaseModel]:
    """Template defaults for a DGM object (matches the BIM.HH DGM schema)."""
    return [Pset_Objektinformation_DGM(), default_bim_hamburg_hyperlink()]


def terrain_part_psets(
    label: str,
    guide_records: Optional[Sequence[object]],
    *,
    dgm_psets: Optional[Sequence[BaseModel]] = None,
) -> List[BaseModel]:
    """Psets for one guided land-use part — the single source both apps share.

    ``label`` is a part label from
    :func:`BIMFabrikHH_core.apps.terrain.processing.build_landuse_parts`.
    The leftover ``DGM`` part gets ``dgm_psets`` (or the DGM defaults); the
    merged ``Parcels`` part and every Nutzung type get an
    ``Pset_Objektinformation`` summarizing their ALKIS features plus the
    BIM.Hamburg hyperlink. :class:`TerrainGenericApp` uses these Pydantic
    models directly; :class:`TerrainRustApp` serializes them for Rust, so the
    written psets are identical.
    """
    from BIMFabrikHH_core.data_models.streets import (
        PARCELS_LABEL,
        pset_for_nutzung_group,
        pset_for_parcel_group,
    )

    if label == "DGM":
        return list(dgm_psets) if dgm_psets is not None else default_terrain_psets()
    hyperlink = default_bim_hamburg_hyperlink()
    if label == PARCELS_LABEL:
        return [pset_for_parcel_group(guide_records or []), hyperlink]
    return [pset_for_nutzung_group(guide_records or [], label=label), hyperlink]


__all__ = [
    "RgbTuple",
    "DEFAULT_TERRAIN_RGB",
    "DEFAULT_TERRAIN_LAYER",
    "TERRAIN_NUTZART_RGB",
    "TERRAIN_NUTZART_LAYER",
    "safe_label",
    "color_for_label",
    "terrain_part_style",
    "default_terrain_psets",
    "terrain_part_psets",
]
