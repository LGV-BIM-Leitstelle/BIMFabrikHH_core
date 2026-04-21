"""
Generic City Model App
======================

Build an IFC LoD1/LoD2 city model from a list of :class:`Building`
records using the ``ifcfactory`` ``BIMFactoryElement`` pipeline.

Mirrors the open-house tutorial pattern used by
:class:`TerrainGenericApp`: each building becomes a single
``IfcBuildingElementProxy`` whose representation is a
:class:`ifcfactory.MeshRepresentation` wrapped in
:class:`ifcfactory.Style` for colour + CAD layer. Psets are attached
via the element's ``psets`` list — ``Pset_Objektinformation`` (a
:class:`Pset_Objektinformation_CityModel` built from
``building.attributes``) plus a default :class:`Pset_Hyperlink`.

Shares the parsing pipeline (:func:`parse_gml_files`) and the
basepoint helper (:func:`place_basepoint`) with :class:`CityBasicApp`.

LoD2 voids
----------

``Building.faces_with_voids`` is passed through to
``MeshRepresentation.faces`` as nested ring lists (outer + inner). Any
atrium / courtyard that ``IfcShapeBuilder.mesh`` cannot represent as a
true ``IfcIndexedPolygonalFaceWithVoids`` will silently fall back to a
closed polygon. If faithful LoD2 voids are required, use
:class:`CityBasicApp` instead.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple, Union

from ifcfactory import BIMFactoryElement, MeshRepresentation, Style
from pydantic import BaseModel

from BIMFabrikHH_core.apps.city._ifc_common import clean_polygon_ring, parse_face_with_voids
from BIMFabrikHH_core.apps.city.processing import parse_gml_files
from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateOperation, CoordinateSystem
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink, default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import (
    Building,
    Pset_Objektinformation_CityModel,
    city_attrs_to_pset,
)

logger = get_level_logger("city_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_CITY_RGB: RgbTuple = (1.0, 1.0, 0.498)
_DEFAULT_CITY_LAYER: str = "_BIM_Stadtmodell"
_DEFAULT_OUTPUT_NAME: str = "output_citymodel_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 8.0

PhaseTimings = dict


class CityGenericApp:
    """Record-builder city-model app built on ``ifcfactory``.

    :meth:`build_ifc` takes a ``List[Building]`` and writes one
    ``IfcBuildingElementProxy`` per building, all attached to the
    project ``IfcBuilding`` in a single O(n) batch via
    :meth:`BIMFactoryElement.build_in`. :meth:`from_gml_files` chains
    the GML parser and the IFC builder.
    """

    @staticmethod
    def build_ifc(
        buildings: List[Building],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: RgbTuple = _DEFAULT_CITY_RGB,
        cad_layer: str = _DEFAULT_CITY_LAYER,
        transparency: float = 0.0,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """Build an IFC file from a list of :class:`Building` records.

        Args:
            buildings: Pre-parsed :class:`Building` records.
            request_params: Project metadata (containers, bbox). The
                WGS84 bbox, if present, is used as the fallback
                basepoint origin.
            output_path: Full path to write the IFC to. When ``None``,
                the file is written to ``PathConfig.OUTPUT / output_name``.
            output_name: Default filename when ``output_path`` is ``None``.
            coordinate_system: Override the default EPSG:25832 CRS.
            coordinate_operation: Override the default coordinate operation.
            color: RGB as ``(R, G, B)`` in 0-255 **or** normalized 0-1 floats.
            cad_layer: CAD layer assigned to every building mesh.
            transparency: 0.0 = opaque, 1.0 = fully transparent.
            pset_hyperlink: Optional shared :class:`Pset_Hyperlink`. Defaults
                to the BIM.Hamburg homepage entry.
            basepoint_origin: Explicit ``(x, y)`` origin in EPSG:25832.
                When ``None``, falls back to ``request_params.bbox``
                lower-left (reprojected WGS84 → EPSG:25832).
            basepoint_size: Edge length of the basepoint quad (meters).
            on_progress: Optional zero-argument callback invoked after
                each building is built.
            phase_timings: Mutable dict receiving per-phase wall time
                (seconds) under ``project_setup_s``, ``prepare_elements_s``,
                ``build_in_s`` and ``save_s``.

        Returns:
            Path to the saved IFC file, or ``None`` on failure.
        """
        if not buildings:
            logger.error("No buildings to export.")
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
            elements = [
                _city_element_from_building(
                    building=building,
                    color=color,
                    cad_layer=cad_layer,
                    transparency=transparency,
                    shared_hyperlink=shared_hyperlink,
                )
                for building in buildings
            ]
            if phase_timings is not None:
                phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

            _t0 = time.perf_counter()
            BIMFactoryElement.build_in(
                model,
                inst=model_builder.building,
                items=elements,
                on_progress=on_progress,
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
            logger.error(f"Error creating IFC model: {exc}")
            import traceback

            traceback.print_exc()
            return None

    @classmethod
    def from_gml_files(
        cls,
        gml_files: Sequence[Union[str, Path]],
        *,
        request_params: RequestParams,
        folder_path: Optional[Union[str, Path]] = None,
        building_id_filter: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: RgbTuple = _DEFAULT_CITY_RGB,
        cad_layer: str = _DEFAULT_CITY_LAYER,
        transparency: float = 0.0,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
    ) -> Optional[Path]:
        """One-shot: parse CityGML tiles, then build the IFC.

        Uses the WGS84 bbox from ``request_params`` to crop the parser
        and — when ``basepoint_origin`` is not given — as the fallback
        basepoint origin.
        """
        buildings = parse_gml_files(
            gml_files,
            folder_path=folder_path,
            bbox_wgs84=request_params.bbox_as_wgs84_tuple,
            building_id_filter=building_id_filter,
        )
        return cls.build_ifc(
            buildings,
            request_params=request_params,
            output_path=output_path,
            output_name=output_name,
            coordinate_system=coordinate_system,
            coordinate_operation=coordinate_operation,
            color=color,
            cad_layer=cad_layer,
            transparency=transparency,
            pset_hyperlink=pset_hyperlink,
            basepoint_origin=basepoint_origin,
            basepoint_size=basepoint_size,
            on_progress=on_progress,
            phase_timings=phase_timings,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _mesh_faces_from_building(building: Building) -> List:
    """Combine ``building.faces`` and ``building.faces_with_voids`` into the
    list shape expected by :class:`MeshRepresentation`.

    ``MeshRepresentation.faces`` is ``List[Union[List[int], List[List[int]]]]``
    — each face is either a single ring or a list of rings (outer + inner).
    This lets us pass voids through when ``IfcShapeBuilder.mesh`` supports
    them, and silently fall back to a closed polygon otherwise.
    """
    mesh_faces: List = []

    for ring in building.faces or []:
        cleaned = clean_polygon_ring(ring)
        if len(cleaned) >= 3:
            mesh_faces.append(cleaned)

    for entry in building.faces_with_voids or []:
        parsed = parse_face_with_voids(entry)
        if parsed is None:
            continue
        outer, inners = parsed
        mesh_faces.append([outer, *inners] if inners else outer)

    return mesh_faces


def _city_element_from_building(
    *,
    building: Building,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    shared_hyperlink: Pset_Hyperlink,
) -> BIMFactoryElement:
    """Wrap a single :class:`Building` in a styled ``BIMFactoryElement``."""
    vertices = [tuple(map(float, v)) for v in building.vertices]
    faces = _mesh_faces_from_building(building)

    mesh_item = MeshRepresentation(vertices=vertices, faces=faces)
    styled_mesh = Style(
        item=mesh_item,
        rgb=color,
        transparency=transparency,
        cad_layer=cad_layer,
    )

    pset_obj = city_attrs_to_pset(building.attributes)

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=building.id,
        qsets=False,
        children=[styled_mesh],
        psets=[pset_obj, shared_hyperlink],
    )


__all__ = ["CityGenericApp"]
