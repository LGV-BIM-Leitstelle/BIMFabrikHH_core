"""
Generic Wasserschutzgebiete App
===============================

Extruded polygon slabs per :class:`WasserschutzgebietRecord` with
``ifcfactory`` ``Polygon`` + ``Extrusion`` + ``Style`` (same idea as
:class:`StandardProfileBuilder`).

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
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Hyperlink,
    default_bim_hamburg_hyperlink,
)
from BIMFabrikHH_core.data_models.wasserschutzgebiete import (
    WasserschutzgebietRecord,
    collect_wasserschutz_psets,
)

logger = get_logger("wasserschutzgebiete_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_RGB: RgbTuple = (64, 128, 200)
_DEFAULT_LAYER: str = "_BIM_Wasserschutzgebiet"
_DEFAULT_OUTPUT_NAME: str = "output_wasserschutzgebiete_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 8.0
_DEFAULT_EXTRUSION_DEPTH_M: float = 2.0

PhaseTimings = dict


def _element_name(record: WasserschutzgebietRecord) -> str:
    base = record.gebietsname or "WSG"
    zone = record.schutzzone or ""
    suffix = f"_{record.feature_id}"
    if zone:
        return f"{base}_{zone}{suffix}".replace(" ", "_")[:120]
    return f"{base}{suffix}".replace(" ", "_")[:120]


def _wsg_element_from_record(
    *,
    record: WasserschutzgebietRecord,
    xy_ring: List[Tuple[float, float]],
    extrusion_depth: float,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    shared_hyperlink: Pset_Hyperlink,
    include_property_sets: bool,
) -> BIMFactoryElement:
    closed = list(xy_ring)
    if not closed or closed[0] != closed[-1]:
        closed = closed + [closed[0]]

    profile = Polygon(points=closed)
    extruded = Extrusion(basis=profile, depth=extrusion_depth)
    styled = Style(item=extruded, rgb=color, transparency=transparency, cad_layer=cad_layer)

    pset_models: List[BaseModel] = collect_wasserschutz_psets(record, include_property_sets=include_property_sets)
    element_psets: List[BaseModel] = [*pset_models, shared_hyperlink]

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=_element_name(record),
        qsets=False,
        children=[styled],
        psets=element_psets,
    )


class WasserschutzgebieteGenericApp:
    """Record-builder: ``list[WasserschutzgebietRecord]`` → extruded IFC solids."""

    @staticmethod
    def build_ifc(
        records: List[WasserschutzgebietRecord],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: RgbTuple = _DEFAULT_RGB,
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
        """Write one ``IfcBuildingElementProxy`` per record (extruded footprint).

        Psets come from ``record.psets`` (plus default hyperlink), same pattern as
        :class:`TreesGenericApp` / ``collect_pydantic_psets``.
        """
        if not records:
            logger.error("No Wasserschutzgebiet records to export.")
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
                xy = ring_xy_to_epsg25832(rec.exterior_ring, rec.geometry_crs)
                if len(xy) < 3:
                    logger.warning("Skipping feature %s: ring too small in EPSG:25832", rec.feature_id)
                    continue
                elements.append(
                    _wsg_element_from_record(
                        record=rec,
                        xy_ring=xy,
                        extrusion_depth=extrusion_depth_m,
                        color=color,
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


__all__ = ["WasserschutzgebieteGenericApp"]
