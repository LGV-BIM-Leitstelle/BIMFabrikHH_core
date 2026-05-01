"""
Generic Trees App
=================

Build an IFC tree model from a list of :class:`TreeRecord` using the
``ifcfactory`` + ``BIMFactoryElement`` batched-build pipeline. Optional
Pydantic property-set templates are attached per tree.

This module replaces the former ``app_pydantic.py`` / ``BaumPydanticApp``.
It follows the record-builder contract declared in
:class:`BIMFabrikHH_core.apps.interface.RecordBuilderApp` (structural).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from ifcfactory import BIMFactoryElement

from BIMFabrikHH_core.apps.trees.processing import collect_pydantic_psets, resolve_tree_dimensions
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.geometry.tree_objects_generic import RgbTuple, create_tree_element
from BIMFabrikHH_core.core.model_creator import init_ifc_project, validate_ifc
from BIMFabrikHH_core.data_models import TreeRecord
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates

DEFAULT_OUTPUT_NAME = "output_trees_generic.ifc"
DEFAULT_TRUNK_COLOR: RgbTuple = (112, 69, 46)
DEFAULT_CROWN_COLOR: RgbTuple = (33, 128, 46)
DEFAULT_TRUNK_LAYER = "_BIM_SBK_Stamm"
DEFAULT_CROWN_LAYER = "_BIM_SBK_Krone"


class TreesGenericApp:
    """Record-builder app: ``list[TreeRecord] -> IFC path``."""

    @staticmethod
    def build_ifc(
        records: List[TreeRecord],
        *,
        output_path: Optional[Union[str, Path]] = None,
        include_property_sets: bool = True,
        trunk_color: RgbTuple = DEFAULT_TRUNK_COLOR,
        crown_color: RgbTuple = DEFAULT_CROWN_COLOR,
        trunk_layer: str = DEFAULT_TRUNK_LAYER,
        crown_layer: str = DEFAULT_CROWN_LAYER,
        name_prefix: str = "",
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = 1.0,
        basepoint_psets: Optional[Dict[str, Any]] = None,
        bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
        validate: bool = False,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[Dict[str, float]] = None,
    ) -> Path:
        """Build an IFC model from a list of :class:`TreeRecord`.

        Args:
            records: Pre-prepared tree records.
            output_path: Target IFC path. If ``None`` the file is written to the
                package output directory using ``DEFAULT_OUTPUT_NAME``.
            include_property_sets: Attach the Pydantic psets on each record.
            trunk_color / crown_color: RGB as ``(R, G, B)`` in 0-255 **or**
                normalized 0-1 floats (``ifcfactory.Style`` accepts both).
            trunk_layer / crown_layer: CAD layer names assigned via ``Style``.
            name_prefix: Prepended to every IFC tree name (e.g. ``"SBK_"``).
            basepoint_origin: Optional ``(x, y)`` in EPSG:25832 for the
                Nullpunktobjekt quad. When ``None``, ``bbox_wgs84`` may supply
                placement (lower-left reprojected); if both are unset, no
                basepoint is written (same contract as :func:`place_basepoint`).
            basepoint_size: Edge length of the basepoint quad (metres); mirrors
                :class:`TreesBasicApp`.
            basepoint_psets: Optional property-set payload forwarded to
                :func:`place_basepoint`.
            bbox_wgs84: Optional ``(min_lon, min_lat, max_lon, max_lat)`` used
                only when ``basepoint_origin`` is ``None``.
            validate: When ``True``, run ``ifcopenshell.validate --rules`` on
                the written file.
            on_progress: Called after each tree is built (progress reporting).
            phase_timings: Mutable dict receiving per-phase wall time (seconds)
                under the keys ``project_setup_s``, ``prepare_elements_s``,
                ``build_in_s``, ``basepoint_s`` (when applicable) and ``save_s``.

        Returns:
            Absolute path of the saved IFC file.
        """
        _t0 = time.perf_counter()
        model_builder = init_ifc_project(
            project_name="Trees_Generic_Project",
            site_name="Trees_Generic_Site",
            coordinate_system=CoordinateSystemTemplates.gauss_kruger_hamburg(),
        )
        if phase_timings is not None:
            phase_timings["project_setup_s"] = time.perf_counter() - _t0

        model = model_builder.model
        site = model_builder.site

        # Build all tree elements in memory first, then attach them to the site
        # in a single BIMFactoryElement.build_in() — O(n) instead of O(n²).
        tree_elements = []
        _t0 = time.perf_counter()
        for idx, record in enumerate(records, 1):
            try:
                tree_elements.append(
                    _tree_element_from_record(
                        record=record,
                        idx=idx,
                        include_property_sets=include_property_sets,
                        trunk_color=trunk_color,
                        crown_color=crown_color,
                        trunk_layer=trunk_layer,
                        crown_layer=crown_layer,
                        name_prefix=name_prefix,
                    )
                )
            except Exception as e:
                logging.error("Failed to create tree %d: %s", idx, e)
                continue

        if phase_timings is not None:
            phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

        _t0 = time.perf_counter()
        BIMFactoryElement.build_in(model, inst=site, items=tree_elements, on_progress=on_progress)
        if phase_timings is not None:
            phase_timings["build_in_s"] = time.perf_counter() - _t0

        if basepoint_origin is not None or bbox_wgs84 is not None:
            _t_bp = time.perf_counter()
            place_basepoint(
                model=model,
                site=site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=None if basepoint_origin is not None else bbox_wgs84,
                size=basepoint_size,
                psets=basepoint_psets or {},
            )
            if phase_timings is not None:
                phase_timings["basepoint_s"] = time.perf_counter() - _t_bp

        _t0 = time.perf_counter()
        file_path = model_builder.save_ifc_to_output(DEFAULT_OUTPUT_NAME, output_path=output_path)
        if phase_timings is not None:
            phase_timings["save_s"] = time.perf_counter() - _t0

        result = Path(str(file_path))
        logging.info("IFC model saved to %s", result)

        if validate:
            validate_ifc(result)

        return result


def _tree_element_from_record(
    *,
    record: TreeRecord,
    idx: int,
    include_property_sets: bool,
    trunk_color: RgbTuple,
    crown_color: RgbTuple,
    trunk_layer: str,
    crown_layer: str,
    name_prefix: str,
):
    tree_name = record.name or f"Baum_{idx:03d}"

    dims = resolve_tree_dimensions(record)
    pset_templates = collect_pydantic_psets(record, include_property_sets=include_property_sets)

    return create_tree_element(
        position=record.position,
        crown_radius=dims.crown_radius,
        trunk_radius=dims.trunk_radius,
        trunk_height=dims.trunk_height,
        crown_detail=record.detail,
        trunk_segments=record.segments,
        psets=pset_templates,
        trunk_color=trunk_color,
        crown_color=crown_color,
        name=tree_name,
        name_prefix=name_prefix,
        trunk_layer=trunk_layer,
        crown_layer=crown_layer,
    )
