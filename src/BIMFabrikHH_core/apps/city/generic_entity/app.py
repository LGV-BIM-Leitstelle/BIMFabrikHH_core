"""
City `generic_entity` export — typed IFC products via `ifcfactory`.

Each CityGML `Building` becomes one `IfcBuilding` whose children are
semantically mapped surfaces (`IfcWall`, `IfcRoof`, `IfcSlab`, …)
built from `ifcfactory.MeshRepresentation` + `ifcfactory.Style`.
Unlike `CityGenericApp` each surface is a separate typed IFC element
rather than one merged proxy mesh.

Custom geometric quantities (area, perimeter, tilt) are stored in
`Pset_BIMFabrikHH_Quantities` on each surface element via
`BIMFabrikHH_core.apps.city.generic_entity.quantities`.
`ifc5d` QTO is run once in batch after all elements are built; disable with
`export_quantity_sets=False`.

CityGML profile `"1.0"` matches Hamburg / Sachsen tiles; use `"2.0"` when
the file declares CityGML 2 / GML 3.2 namespaces.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import ifcopenshell
from ifcfactory import BIMFactoryElement, MeshRepresentation, Style

from BIMFabrikHH_core.apps.city.generic_entity.models import (
    BoundaryPolygon,
    BoundarySurfaceMapping,
    IfcProductClass,
    mapping_registry,
)
from BIMFabrikHH_core.apps.city.generic_entity.parser import (
    CitygmlProfile,
    parse_typed_gml_files,
)
from BIMFabrikHH_core.apps.city.generic_entity.quantities import (
    compute_boundary_quantities,
    face_quantities_to_pset,
)
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import (
    Pset_Hyperlink,
    default_bim_hamburg_hyperlink,
)
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import (
    TypedCityBuilding,
    city_attrs_to_pset,
)

logger = get_logger("city_generic_entity_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_RGB: RgbTuple = (1.0, 1.0, 0.498)
_DEFAULT_LAYER: str = "_BIM_Stadtmodell_entity"
_DEFAULT_OUTPUT_NAME: str = "output_citymodel_generic_entity.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 8.0

_ROOF_COLOR: RgbTuple = (1.0, 0.0, 0.0)

PhaseTimings = dict


def _strip_ifc_quantity_volumes(model: ifcopenshell.file) -> None:
    """Remove ``IfcQuantityVolume`` rows from every ``IfcElementQuantity``.

    Keeps length / area / count / … from ``ifc5d`` while dropping bogus volumes
    on thin mesh ``IfcWall`` / … geometry.
    """
    for eq in model.by_type("IfcElementQuantity"):
        quants = list(eq.Quantities or ())
        drop = [q for q in quants if q.is_a("IfcQuantityVolume")]
        if not drop:
            continue
        eq.Quantities = tuple(q for q in quants if q not in drop)
        for q in drop:
            model.remove(q)


def _ifc_root_name_from_gml(gml_id: str, gml_name: Optional[str]) -> str:
    """``IfcRoot.Name``: ``{gml:name}_{gml:id}`` when a name exists, else ``gml:id``."""
    label = (gml_name or "").strip()
    if label:
        return f"{label}_{gml_id}"
    return gml_id


def _styled_mesh_for_boundary(
    boundary: BoundaryPolygon,
    *,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
) -> Style:
    """Build a ``Style`` wrapping a ``MeshRepresentation`` for one boundary polygon.

    When ``boundary.interior_rings`` is non-empty the face is encoded as a
    nested list ``[[outer_indices], [inner1_indices], …]`` so that
    ``IfcShapeBuilder.mesh`` can emit ``IfcIndexedPolygonalFaceWithVoids``
    for courtyard / atrium geometry.
    """
    exterior: List[Tuple[float, float, float]] = [tuple(map(float, p)) for p in boundary.ring]
    vertices: List[Tuple[float, float, float]] = list(exterior)

    if boundary.interior_rings:
        outer_indices = list(range(len(exterior)))
        offset = len(exterior)
        inner_index_rings: List[List[int]] = []
        for inner_ring in boundary.interior_rings:
            inner: List[Tuple[float, float, float]] = [tuple(map(float, p)) for p in inner_ring]
            inner_index_rings.append(list(range(offset, offset + len(inner))))
            vertices.extend(inner)
            offset += len(inner)
        faces: List = [[outer_indices, *inner_index_rings]]
    else:
        faces = [list(range(len(exterior)))]

    mesh_item = MeshRepresentation(vertices=vertices, faces=faces)
    return Style(item=mesh_item, rgb=color, transparency=transparency, cad_layer=cad_layer)


def _element_for_boundary(
    boundary: BoundaryPolygon,
    *,
    building_root_name: str,
    index: int,
    ifc_type: IfcProductClass,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
) -> BIMFactoryElement:
    name_parts = [building_root_name, boundary.surface_type, str(index)]
    if boundary.source_part_id:
        name_parts.insert(1, boundary.source_part_id)
    element_name = "_".join(name_parts)

    effective_color = _ROOF_COLOR if boundary.surface_type == "RoofSurface" else color
    styled = _styled_mesh_for_boundary(boundary, color=effective_color, cad_layer=cad_layer, transparency=transparency)
    qty_pset = face_quantities_to_pset(compute_boundary_quantities(boundary))

    return BIMFactoryElement(
        type=ifc_type,
        name=element_name,
        qsets=False,  # quantify runs once in batch after all elements are built
        children=[styled],
        psets=[qty_pset],
    )


def _bim_building_from_typed(
    tb: TypedCityBuilding,
    *,
    kind_to_ifc: Dict[str, IfcProductClass],
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    shared_hyperlink: Pset_Hyperlink,
) -> BIMFactoryElement:
    """Build one ``IfcBuilding`` element with typed surface children.

    Each surface becomes a typed IFC element (``IfcWall``, ``IfcRoof``, …)
    with its own mesh representation and ``Pset_BIMFabrikHH_Quantities``.
    """
    root_name = _ifc_root_name_from_gml(tb.id, tb.gml_name)
    surface_children: List[BIMFactoryElement] = [
        _element_for_boundary(
            boundary,
            building_root_name=root_name,
            index=idx,
            ifc_type=kind_to_ifc.get(boundary.surface_type, "IfcBuildingElementProxy"),
            color=color,
            cad_layer=cad_layer,
            transparency=transparency,
        )
        for idx, boundary in enumerate(tb.boundaries)
    ]
    pset_obj = city_attrs_to_pset(tb.attributes)
    return BIMFactoryElement(
        type="IfcBuilding",
        name=root_name,
        qsets=False,
        children=surface_children,
        psets=[pset_obj, shared_hyperlink],
    )


class CityGenericEntityApp:
    """CityGML → IFC using ``ifcfactory``: one ``IfcBuilding`` per city building."""

    @staticmethod
    def build_ifc(
        buildings: List[TypedCityBuilding],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: RgbTuple = _DEFAULT_RGB,
        cad_layer: str = _DEFAULT_LAYER,
        transparency: float = 0.0,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        mapping_extra: Tuple[BoundarySurfaceMapping, ...] = (),
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
        export_quantity_sets: bool = True,
        include_volume_in_quantity_sets: bool = False,
    ) -> Optional[Path]:
        if not buildings:
            logger.error("CityGenericEntityApp.build_ifc: no buildings.")
            return None

        kind_to_ifc = mapping_registry(mapping_extra)

        try:
            _t0 = time.perf_counter()
            model_builder = init_ifc_project(
                request_params=request_params,
                coordinate_system=coordinate_system,
                coordinate_operation=coordinate_operation,
                building_name="",
            )
            model = model_builder.model
            site = model_builder.site
            if model is None or site is None:
                logger.error("Failed to create IFC model or site")
                return None

            if phase_timings is not None:
                phase_timings["project_setup_s"] = time.perf_counter() - _t0

            shared_hyperlink = pset_hyperlink or default_bim_hamburg_hyperlink()

            _t0 = time.perf_counter()
            prepared = [
                _bim_building_from_typed(
                    tb,
                    kind_to_ifc=kind_to_ifc,
                    color=color,
                    cad_layer=cad_layer,
                    transparency=transparency,
                    shared_hyperlink=shared_hyperlink,
                )
                for tb in buildings
            ]
            if phase_timings is not None:
                phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

            _t0 = time.perf_counter()
            BIMFactoryElement.build_in(model, site, prepared, on_progress=on_progress)
            if phase_timings is not None:
                phase_timings["build_in_s"] = time.perf_counter() - _t0

            place_basepoint(
                model=model,
                site=site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=request_params.bbox_as_wgs84_tuple,
                size=basepoint_size,
            )

            if export_quantity_sets:
                _t0 = time.perf_counter()
                BIMFactoryElement.batch_quantify(model)
                if phase_timings is not None:
                    phase_timings["quantify_s"] = time.perf_counter() - _t0
                if not include_volume_in_quantity_sets:
                    _strip_ifc_quantity_volumes(model)

            _t0 = time.perf_counter()
            saved_path = model_builder.save_ifc_to_output(output_name, output_path=output_path)
            if phase_timings is not None:
                phase_timings["save_s"] = time.perf_counter() - _t0
            if not saved_path:
                raise RuntimeError("Failed to save IFC file")
            return Path(str(saved_path))

        except Exception as exc:
            logger.error("CityGenericEntityApp.build_ifc failed: %s", exc)
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
        profile: CitygmlProfile = "1.0",
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        color: RgbTuple = _DEFAULT_RGB,
        cad_layer: str = _DEFAULT_LAYER,
        transparency: float = 0.0,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        mapping_extra: Tuple[BoundarySurfaceMapping, ...] = (),
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[PhaseTimings] = None,
        log_boundary_kinds: bool = False,
        export_quantity_sets: bool = True,
        include_volume_in_quantity_sets: bool = False,
    ) -> Optional[Path]:
        typed = parse_typed_gml_files(
            gml_files,
            folder_path=folder_path,
            bbox_wgs84=request_params.bbox_as_wgs84_tuple,
            building_id_filter=building_id_filter,
            profile=profile,
            log_boundary_kinds=log_boundary_kinds,
        )
        return cls.build_ifc(
            typed,
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
            mapping_extra=mapping_extra,
            on_progress=on_progress,
            phase_timings=phase_timings,
            export_quantity_sets=export_quantity_sets,
            include_volume_in_quantity_sets=include_volume_in_quantity_sets,
        )


__all__ = ["CityGenericEntityApp"]
