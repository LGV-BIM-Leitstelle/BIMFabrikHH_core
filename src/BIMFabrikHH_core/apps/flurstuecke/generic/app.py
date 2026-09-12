"""
Generic Flurstuecke App
=======================

ALKIS cadastral parcels as **IfcBuildingElementProxy** volumes: each parcel
footprint is extruded 30 m upwards from ``z = 0``.

Built with the ``ifcfactory`` ``Polygon`` + ``Extrusion`` + ``Style`` pipeline
and the same record-builder / basepoint / pset orchestration as
:class:`WasserschutzgebieteGenericApp`. A multi-part parcel (``MultiPolygon``)
becomes one proxy holding one extrusion per part.

Proxies are contained in the building via ``IfcRelContainedInSpatialStructure``.

Ring coordinates must end up in **EPSG:25832** for the IFC georeferencing
context: either records already carry ``geometry_crs=EPSG:25832``
``(easting, northing)``, or ``EPSG:4326`` ``(lon, lat)`` and are reprojected
via :func:`BIMFabrikHH_core.core.ogc_extractor.ring_xy_to_epsg25832`.

Geometry uses **map metres** (full easting / northing in EPSG:25832).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from ifcfactory import BIMFactoryElement, Extrusion, Polygon, Style
from pydantic import BaseModel

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor import ring_xy_to_epsg25832
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_psets_basepoint
from BIMFabrikHH_core.data_models.flurstuecke import (
    FlurstueckRecord,
    collect_flurstueck_psets,
)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Hyperlink,
    default_bim_hamburg_hyperlink,
)

logger = get_logger("flurstuecke_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]
PhaseTimings = dict

_DEFAULT_LAYER: str = "_BIM_Flurstueck"
_DEFAULT_OUTPUT_NAME: str = "output_flurstuecke_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0
_DEFAULT_EXTRUSION_DEPTH_M: float = 30.0


def _flurstueck_element_from_record(
    *,
    record: FlurstueckRecord,
    xy_rings: List[List[Tuple[float, float]]],
    extrusion_depth: float,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    shared_hyperlink: Pset_Hyperlink,
    include_property_sets: bool,
) -> BIMFactoryElement:
    """One ``IfcBuildingElementProxy`` per parcel, one extrusion per MultiPolygon part."""
    styled_parts: List[Style] = []
    for ring in xy_rings:
        closed = list(ring)
        if not closed or closed[0] != closed[-1]:
            closed += [closed[0]]

        profile = Polygon(points=closed)
        extruded = Extrusion(basis=profile, depth=extrusion_depth)
        styled_parts.append(Style(item=extruded, rgb=color, transparency=transparency, cad_layer=cad_layer))

    pset_models: List[BaseModel] = collect_flurstueck_psets(record, include_property_sets=include_property_sets)
    element_psets: List[BaseModel] = [*pset_models, shared_hyperlink]

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=record.element_name,
        qsets=False,
        children=styled_parts,
        psets=element_psets,
    )


class FlurstueckeGenericApp:
    """Record-builder: ``list[FlurstueckRecord]`` → extruded ``IfcBuildingElementProxy`` parcels."""

    @staticmethod
    def build_ifc(
        records: List[FlurstueckRecord],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_LAYER,
        transparency: float = 0.0,
        extrusion_depth_m: float = _DEFAULT_EXTRUSION_DEPTH_M,
        include_property_sets: bool = True,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """Write one ``IfcBuildingElementProxy`` per record, extruded from ``z = 0``.

        Colour is ``record.element_color`` unless ``color`` is set (one colour for all).

        Psets come from ``record.psets`` (plus default hyperlink), same pattern as
        :class:`WasserschutzgebieteGenericApp` / :class:`StreetsGenericApp`.
        """
        if not records:
            logger.error("No Flurstueck records to export.")
            return None

        try:
            _t0 = time.perf_counter()
            model_builder = init_ifc_project(
                request_params=request_params,
                coordinate_system=coordinate_system,
                coordinate_operation=coordinate_operation,
            )
            model = model_builder.model
            if model is None:
                logger.error("Failed to create IFC model")
                return None

            if phase_timings is not None:
                phase_timings["project_setup_s"] = time.perf_counter() - _t0

            shared_hyperlink = pset_hyperlink or default_bim_hamburg_hyperlink()

            _t0 = time.perf_counter()
            elements: List[BIMFactoryElement] = []
            for rec in records:
                xy_rings = [
                    xy for xy in (ring_xy_to_epsg25832(ring, rec.geometry_crs) for ring in rec.rings) if len(xy) >= 3
                ]
                if not xy_rings:
                    logger.warning("Skipping feature %s: no ring with 3+ vertices in EPSG:25832", rec.feature_id)
                    continue
                elements.append(
                    _flurstueck_element_from_record(
                        record=rec,
                        xy_rings=xy_rings,
                        extrusion_depth=extrusion_depth_m,
                        color=color if color is not None else rec.element_color,
                        cad_layer=cad_layer,
                        transparency=transparency,
                        shared_hyperlink=shared_hyperlink,
                        include_property_sets=include_property_sets,
                    )
                )
                if on_progress:
                    on_progress()

            if phase_timings is not None:
                phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

            if not elements:
                logger.error("No valid geometries after preparing rings.")
                return None

            _t0 = time.perf_counter()
            BIMFactoryElement.build_in(
                model,
                inst=model_builder.building,
                items=elements,
                on_progress=None,
            )
            if phase_timings is not None:
                phase_timings["build_in_s"] = time.perf_counter() - _t0

            place_basepoint(
                model=model,
                site=model_builder.site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=request_params.bbox_as_wgs84_tuple,
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


__all__ = ["FlurstueckeGenericApp"]
