"""
Generic Streets App
===================

Drapes ALKIS ``Nutzung`` traffic polygons (``Strassenverkehr``, ``Weg``,
``Bahnverkehr``) onto a DGM and writes one ``IfcBuildingElementProxy`` per
feature, using the ``ifcfactory`` ``BIMFactoryElement`` +
``MeshRepresentation`` + ``Style`` pipeline — the same mesh pattern as
:class:`TerrainGenericApp`, and the same record-builder / basepoint / pset
orchestration as :class:`WasserschutzgebieteGenericApp`.

Geometry comes from ``alkis_vereinfacht / Nutzung``; ground elevation comes
from the ``Digitales Höhenmodell Hamburg DGM 1`` GeoTIFF tiles. Both share
EPSG:25832 (ETRS89 / UTM 32N) and NHN heights.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple, Union

from ifcfactory import BIMFactoryElement, MeshRepresentation, Style
from pydantic import BaseModel

from BIMFabrikHH_core.apps.streets.processing import (
    DEFAULT_EDGE_SPACING_M,
    DEFAULT_VERTICAL_OFFSET_M,
    DrapedStreet,
    drape_streets,
)
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_psets_basepoint
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Hyperlink,
    default_bim_hamburg_hyperlink,
)
from BIMFabrikHH_core.data_models.streets import StreetRecord, collect_street_psets

logger = get_logger("streets_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_RGB: RgbTuple = (80, 80, 80)
_NUTZART_RGB: Dict[str, RgbTuple] = {
    "Strassenverkehr": (80, 80, 80),
    "Weg": (140, 120, 90),
    "Bahnverkehr": (50, 50, 50),
}
_DEFAULT_LAYER: str = "_BIM_Strassen"
_DEFAULT_OUTPUT_NAME: str = "output_streets_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0

PhaseTimings = dict


def _element_name(record: StreetRecord) -> str:
    base = record.name or record.bez or record.nutzart or "Nutzung"
    return f"{base}_{record.feature_id}".replace(" ", "_")[:120]


def _color_for(record: StreetRecord, fallback: RgbTuple) -> RgbTuple:
    return _NUTZART_RGB.get(record.nutzart, fallback)


def _street_element_from_draped(
    *,
    draped: DrapedStreet,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    shared_hyperlink: Pset_Hyperlink,
    include_property_sets: bool,
) -> Optional[BIMFactoryElement]:
    if draped.is_empty():
        logger.warning("Skipping street %s: empty/degenerate mesh", draped.record.feature_id)
        return None

    mesh_item = MeshRepresentation(vertices=draped.vertices, faces=draped.faces)
    styled = Style(item=mesh_item, rgb=color, transparency=transparency, cad_layer=cad_layer)

    pset_models: List[BaseModel] = collect_street_psets(draped.record, include_property_sets=include_property_sets)
    element_psets: List[BaseModel] = [*pset_models, shared_hyperlink]

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=_element_name(draped.record),
        qsets=False,
        children=[styled],
        psets=element_psets,
    )


class StreetsGenericApp:
    """Record-builder: ``list[StreetRecord]`` + DGM tiles → draped IFC traffic surfaces."""

    @staticmethod
    def build_ifc(
        records: List[StreetRecord],
        *,
        request_params: RequestParams,
        tif_files: Optional[Iterable[Union[str, Path]]] = None,
        folder_path: Optional[Union[str, Path]] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_LAYER,
        transparency: float = 0.0,
        vertical_offset_m: float = DEFAULT_VERTICAL_OFFSET_M,
        edge_spacing_m: float = DEFAULT_EDGE_SPACING_M,
        default_elevation: float = 0.0,
        include_property_sets: bool = True,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """Drape ``records`` on the DGM and write one styled mesh per Nutzung feature.

        When ``color`` is ``None``, RGB is chosen from ``nutzart``
        (``Strassenverkehr`` / ``Weg`` / ``Bahnverkehr``).
        """
        if not records:
            logger.error("No street records to export.")
            return None

        try:
            _t0 = time.perf_counter()
            model_builder = init_ifc_project(request_params=request_params, building_name="Strassen")
            model = model_builder.model
            if model is None:
                logger.error("Failed to create IFC model")
                return None
            if phase_timings is not None:
                phase_timings["project_setup_s"] = time.perf_counter() - _t0

            shared_hyperlink = pset_hyperlink or default_bim_hamburg_hyperlink()

            _t0 = time.perf_counter()
            draped_streets = drape_streets(
                records,
                list(tif_files) if tif_files is not None else [],
                folder_path=folder_path,
                vertical_offset_m=vertical_offset_m,
                edge_spacing_m=edge_spacing_m,
                default_elevation=default_elevation,
            )
            if phase_timings is not None:
                phase_timings["drape_s"] = time.perf_counter() - _t0

            _t0 = time.perf_counter()
            elements: List[BIMFactoryElement] = []
            for draped in draped_streets:
                element = _street_element_from_draped(
                    draped=draped,
                    color=color if color is not None else _color_for(draped.record, _DEFAULT_RGB),
                    cad_layer=cad_layer,
                    transparency=transparency,
                    shared_hyperlink=shared_hyperlink,
                    include_property_sets=include_property_sets,
                )
                if element is not None:
                    elements.append(element)
                if on_progress:
                    on_progress()
            if phase_timings is not None:
                phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

            if not elements:
                logger.error("No valid street geometries after draping.")
                return None

            _t0 = time.perf_counter()
            BIMFactoryElement.build_in(model, inst=model_builder.building, items=elements, on_progress=None)
            if phase_timings is not None:
                phase_timings["build_in_s"] = time.perf_counter() - _t0

            place_basepoint(
                model=model,
                site=model_builder.site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=(None if basepoint_origin is not None else request_params.bbox_as_wgs84_tuple),
                size=basepoint_size,
                psets=extract_psets_basepoint(request_params.containers or []),
            )

            _t0 = time.perf_counter()
            saved_path = model_builder.save_ifc_to_output(output_name, output_path=output_path)
            if phase_timings is not None:
                phase_timings["save_s"] = time.perf_counter() - _t0
            if not saved_path:
                raise RuntimeError("Failed to save IFC file")
            return Path(str(saved_path))

        except Exception as exc:
            logger.error("Error creating IFC model: %s", exc)
            import traceback

            traceback.print_exc()
            return None


__all__ = ["StreetsGenericApp"]
