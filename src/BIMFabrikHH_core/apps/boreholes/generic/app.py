"""
Generic Boreholes App
=====================

One stacked ``ifcfactory`` ``Cylinder`` per soil layer of a
:class:`BoreholeRecord`, wrapped in ``Transform`` → ``Style`` → ``Cylinder``
like the intern Baugrundaufschluss model.

Each cylinder sits at its lower layer boundary (``lower_height``) with the
layer thickness as height, so the layers of a borehole stack from the
Ansatzpunkt downwards.

Geometry uses **map metres** (full easting / northing in EPSG:25832); the WFS
delivers EPSG:5555, whose horizontal part is EPSG:25832.

The IFC display colour comes from the layer's ``hauptgemengteil`` (DIN 4023),
not from its ``farbe`` code, which stays metadata in
``Pset_Aufschlussbereich``.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Union

from ifcfactory import BIMFactoryElement, Cylinder, Material, Style, Transform
from pydantic import BaseModel

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor import extract_psets_basepoint
from BIMFabrikHH_core.data_models.boreholes import (
    BoreholeLayer,
    BoreholeRecord,
    collect_borehole_psets,
)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink

logger = get_logger("boreholes_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_LAYER_PREFIX: str = "_Bodenaufschluesse"
_DEFAULT_OUTPUT_NAME: str = "output_boreholes_generic.ifc"
_DEFAULT_CYLINDER_RADIUS_M: float = 0.5
_DEFAULT_BASEPOINT_SIZE: float = 8.0

PhaseTimings = dict


def _cad_layer_name(din_color_name: str) -> str:
    """CAD layer per DIN colour, e.g. ``_Bodenaufschluesse_orange``."""
    return f"{_DEFAULT_LAYER_PREFIX}_{din_color_name.replace(' ', '_').lower()}"


def _material_name(farbe: str, din_color_name: str) -> str:
    """Material per ``farbe`` metadata plus DIN colour, as in the intern model."""
    safe_farbe = (farbe or "undefiniert").replace(" ", "_").replace("/", "_")
    for char in "()":
        safe_farbe = safe_farbe.replace(char, "")
    return f"{_DEFAULT_LAYER_PREFIX}_{safe_farbe}_{din_color_name}"


def _element_name(record: BoreholeRecord, layer: BoreholeLayer) -> str:
    """``<Aufschlussbezeichnung>_<Bohrung>_<Nr>``; ``layer_id`` already carries the borehole id."""
    return f"{record.aufschlussbezeichnung}_{layer.layer_id}".replace(" ", "_")[:120]


def _cylinder_element_from_layer(
    *,
    record: BoreholeRecord,
    layer: BoreholeLayer,
    cylinder_radius: float,
    color: Optional[RgbTuple],
    transparency: float,
    materials: Dict[str, Material],
    hyperlink_override: Optional[Pset_Hyperlink],
    include_property_sets: bool,
) -> BIMFactoryElement:
    layer_color: RgbTuple = color if color is not None else layer.visual_rgb
    cad_layer = _cad_layer_name(layer.din_color_name)
    material_name = _material_name(layer.farbe, layer.din_color_name)
    material = materials.get(material_name)
    if material is None:
        material = Material(name=material_name, category="soil", rgb=layer_color, transparency=transparency)
        materials[material_name] = material

    styled = Style(
        item=Cylinder(radius=cylinder_radius, height=layer.thickness),
        rgb=layer_color,
        transparency=transparency,
        cad_layer=cad_layer,
    )
    placed = Transform(
        item=styled,
        translation=(record.easting, record.northing, layer.lower_height),
    )

    # The record already carries its own Pset_Hyperlink built from the borehole id.
    element_psets: List[BaseModel] = collect_borehole_psets(
        record,
        layer,
        include_property_sets=include_property_sets,
    )
    if hyperlink_override is not None:
        element_psets = [pset for pset in element_psets if not isinstance(pset, Pset_Hyperlink)]
        element_psets.append(hyperlink_override)

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        material=material,
        name=_element_name(record, layer),
        qsets=False,
        children=[placed],
        psets=element_psets,
    )


class BoreholesGenericApp:
    """Record-builder: ``list[BoreholeRecord]`` → stacked IFC soil cylinders."""

    @staticmethod
    def build_ifc(
        records: List[BoreholeRecord],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        cylinder_radius_m: float = _DEFAULT_CYLINDER_RADIUS_M,
        color: Optional[RgbTuple] = None,
        transparency: float = 0.0,
        include_property_sets: bool = True,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """Write one ``IfcBuildingElementProxy`` cylinder per soil layer.

        Args:
            records: Pre-parsed :class:`BoreholeRecord` list, e.g. from
                :func:`~BIMFabrikHH_core.apps.boreholes.processing.records_from_boreholeml`.
            request_params: Project / site / building names and bbox.
            output_path: Explicit target file; defaults to the output folder.
            output_name: Filename used when ``output_path`` is ``None``.
            coordinate_system: Override for the georeferencing context.
            coordinate_operation: Override for the map conversion.
            cylinder_radius_m: Radius of every layer cylinder in metres.
            color: Fixed colour for all layers; ``None`` keeps the per-layer
                DIN 4023 colour from ``hauptgemengteil``.
            transparency: Style transparency, ``0.0`` is opaque.
            include_property_sets: Attach the borehole and layer psets.
            pset_hyperlink: Replaces the per-borehole geodienste portal link
                on every element; ``None`` keeps each borehole's own link.
            basepoint_size: Edge length of the basepoint marker.
            on_progress: Called once per finished layer.
            phase_timings: Optional dict filled with per-phase seconds.

        Returns:
            Path of the written IFC file, or ``None`` on failure.
        """
        if not records:
            logger.error("No borehole records to export.")
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
            materials: Dict[str, Material] = {}
            elements: List[BIMFactoryElement] = []
            for record in records:
                for layer in record.layers:
                    elements.append(
                        _cylinder_element_from_layer(
                            record=record,
                            layer=layer,
                            cylinder_radius=cylinder_radius_m,
                            color=color,
                            transparency=transparency,
                            materials=materials,
                            hyperlink_override=pset_hyperlink,
                            include_property_sets=include_property_sets,
                        )
                    )
                    if on_progress:
                        on_progress()

            if phase_timings is not None:
                phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

            if not elements:
                logger.error("No layers found on the given borehole records.")
                return None

            logger.info(
                "Building %d layer cylinder(s) from %d borehole(s), %d material(s)",
                len(elements),
                len(records),
                len(materials),
            )

            _t0 = time.perf_counter()
            BIMFactoryElement.build_in(
                model,
                inst=model_builder.site,
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


__all__ = ["BoreholesGenericApp"]
