"""
"""


from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union

from BIMFabrikHH_core.core.ogc_extractor.geojson import MultiPolygon
from BIMFabrikHH_core.core.ogc_extractor.rings import polygon_rings_to_epsg25832
from ifcfactory import BIMFactoryElement, Boolean, BooleanOperationTypes, Extrusion, MeshRepresentation, Polygon, Style
from pydantic import BaseModel

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor import line_xy_to_epsg25832
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import \
    extract_psets_basepoint
from BIMFabrikHH_core.data_models.biotopes import (BiotopeRecord, BiotopeShape,
                                                   collect_biotope_psets)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation, CoordinateSystem)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Hyperlink, default_bim_hamburg_hyperlink)

logger = get_logger("biotopes_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]
PhaseTimings = dict

_DEFAULT_LAYER: str = "_BIM_Biotop"
_DEFAULT_OUTPUT_NAME: str = "output_biotopes_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0
_DEFAULT_EXTRUSION_DEPTH_M: float = 30.0


class BiotopesGenericApp:
    """Record-builder: ``list[BiotopeRecord]`` → extruded ``IfcBuildingElementProxy`` parcels."""

    @staticmethod
    def build_ifc(
        records: List[BiotopeRecord],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_LAYER,
        transparency: float = 0.5,
        extrusion_depth_m: float = _DEFAULT_EXTRUSION_DEPTH_M,
        include_property_sets: bool = True,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """TODO
        """
        if not records:
            logger.error("No biotope records to export.")
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

            _t0 = time.perf_counter()
            elements: List[BIMFactoryElement] = []
            for rec in records:
                if rec.shape_type == BiotopeShape.AREA:
                    xy_rings: MultiPolygon = [
                        result
                        for polygon in rec.rings
                        if len(polygon.exterior) >= 3
                        and (result := polygon_rings_to_epsg25832(polygon, rec.geometry_crs)) is not None
                    ]
                    if not xy_rings:
                        logger.warning("Skipping feature %s: no ring with 3+ vertices in EPSG:25832", rec.feature_id)
                        continue
                    elements.append(
                        _polygon_biotope_element_from_record(
                            record=rec,
                            multipolygon=xy_rings,
                            extrusion_depth=extrusion_depth_m,
                            color=color if color is not None else rec.element_color,
                            cad_layer=cad_layer,
                            transparency=transparency,
                            overwrite_hyperlink=pset_hyperlink,
                            include_property_sets=include_property_sets,
                        )
                    )
                    if on_progress:
                        on_progress()
                elif rec.shape_type == BiotopeShape.LINES:
                    xy_lines: List[List[Tuple]] = [
                        result
                        for line in rec.lines
                        if (result := line_xy_to_epsg25832(line, rec.geometry_crs)) is not None
                    ]
                    if not xy_lines or not any(xy_lines): 
                        logger.warning("Skipping feature %s: no coordinate line in EPSG:25832", rec.feature_id)
                        continue
                    elements.append(
                        _line_biotope_element_from_record(
                            record=rec,
                            lines=xy_lines,
                            extrusion_depth=extrusion_depth_m,
                            color=color if color is not None else rec.element_color,
                            cad_layer=cad_layer,
                            transparency=transparency,
                            overwrite_hyperlink=pset_hyperlink,
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


def _polygon_biotope_element_from_record(
    *,
    record: BiotopeRecord,
    multipolygon: MultiPolygon,
    extrusion_depth: float,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    overwrite_hyperlink: Optional[Pset_Hyperlink],
    include_property_sets: bool,
) -> BIMFactoryElement:
    """One ``IfcBuildingElementProxy`` per parcel, one extrusion per MultiPolygon part."""
    styled_parts: List[Style] = []
    for polygon in multipolygon:
        if not polygon.exterior:
            continue
        exterior = Polygon(points=polygon.exterior)  # Polygon closes ring if not closed
        holes = [Polygon(points=hole) for hole in polygon.holes]
        profile = exterior

        for hole in holes:
            profile = Boolean(
                operation=BooleanOperationTypes.Difference,
                children=[profile, hole],
            )

        extruded = Extrusion(basis=profile, depth=extrusion_depth)
        styled_parts.append(Style(item=extruded, rgb=color, transparency=transparency, cad_layer=cad_layer))

    pset_models: List[BaseModel] = collect_biotope_psets(record, include_property_sets=include_property_sets)
    element_psets: List[BaseModel] = [*pset_models, overwrite_hyperlink] if overwrite_hyperlink else pset_models

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=record.element_name,  # TODO: find good element name
        qsets=False,
        children=styled_parts,
        psets=element_psets,
    )


def _line_biotope_element_from_record(
    *,
    record: BiotopeRecord,
    lines: List[List[Tuple]],
    extrusion_depth: float,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    overwrite_hyperlink: Optional[Pset_Hyperlink],
    include_property_sets: bool,
) -> BIMFactoryElement:
    """TODO"""
    styled_parts: List[Style] = []
    for line in lines:
        if not line:
            continue
        vertices_zero = [(float(pos[0]), float(pos[1]), 0.0) for pos in line]
        vertices_extruded = [(float(pos[0]), float(pos[1]), extrusion_depth) for pos in line]

        vertices = 2 * vertices_zero # only for initialization, is overwritten
        vertices[::2] = vertices_zero
        vertices[1::2] = vertices_extruded

        faces = [[v, v+1, v+2] for v in range(0,len(vertices)-2)]

        if not vertices or not faces or len(faces) != len(vertices)-2:
            continue

        custom_mesh = MeshRepresentation(vertices=vertices, faces=faces)
        extruded = Extrusion(basis=custom_mesh, depth=extrusion_depth)
        styled_parts.append(Style(item=custom_mesh, rgb=color, transparency=transparency, cad_layer=cad_layer))

    pset_models: List[BaseModel] = collect_biotope_psets(record, include_property_sets=include_property_sets)
    element_psets: List[BaseModel] = [*pset_models, overwrite_hyperlink] if overwrite_hyperlink else pset_models

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=record.element_name,
        qsets=False,
        children=styled_parts,
        psets=element_psets,
    )
