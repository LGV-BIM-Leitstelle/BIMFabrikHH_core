"""
Basic City Model App
====================

Record-builder app that turns a list of :class:`Building` records into
an IFC LoD1/LoD2 city model. Mirrors the trees / terrain basic-app
contract:

- Pure data processing lives in :mod:`BIMFabrikHH_core.apps.city.processing`
  (:func:`parse_gml_files`).
- IFC writing (``ifcopenshell.api``: ``IfcPolygonalFaceSet`` tessellation,
  optional ``IfcIndexedPolygonalFaceWithVoids`` for LoD2 courtyards) lives
  here as private module-level helpers.
- :meth:`CityBasicApp.from_gml_files` is a one-shot convenience that
  chains parsing + IFC building.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import ifcopenshell.api.owner.settings as owner_settings
import numpy as np
from ifcopenshell.api import context, geometry, pset, root, spatial

from BIMFabrikHH_core.apps.city._ifc_common import clean_polygon_ring, parse_face_with_voids
from BIMFabrikHH_core.apps.city.processing import parse_gml_files
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder, init_ifc_project
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateOperation, CoordinateSystem
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink, default_bim_hamburg_hyperlink
from BIMFabrikHH_core.data_models.pydantic_psets_city_model import Building

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_NAME: str = "output_citymodel.ifc"
_DEFAULT_COLOR: Tuple[float, float, float] = (1.0, 1.0, 0.498)
_DEFAULT_LAYER: str = "_BIM_Stadtmodell"
_DEFAULT_BASEPOINT_SIZE: float = 8.0


class CityBasicApp:
    """Record-builder city app: ``List[Building] -> IFC file``."""

    @staticmethod
    def build_ifc(
        buildings: List[Building],
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        coordinate_operation: Optional[CoordinateOperation] = None,
        representation_color: Tuple[float, float, float] = _DEFAULT_COLOR,
        layer_name: str = _DEFAULT_LAYER,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
    ) -> Optional[Path]:
        """Build an IFC city model from a list of :class:`Building` records.

        Args:
            buildings: Pre-parsed ``Building`` records.
            request_params: Project metadata (containers, bbox). The WGS84
                bbox, if present, is used as the **fallback** basepoint
                origin (lower-left corner, reprojected to EPSG:25832).
            output_path: Full path to write the IFC to. When ``None``,
                the file is written to ``PathConfig.OUTPUT / output_name``.
            output_name: Default filename when ``output_path`` is ``None``.
            coordinate_system: Override the default EPSG:25832 CRS (e.g.
                EPSG:25833 for Sachsen tiles).
            coordinate_operation: Override the default coordinate operation.
            representation_color: RGB in normalized 0-1 for building surfaces.
            layer_name: CAD layer assigned to every building representation.
            pset_hyperlink: Optional pre-built :class:`Pset_Hyperlink`.
                Defaults to the BIM.Hamburg homepage link.
            basepoint_origin: Explicit ``(x, y)`` origin in EPSG:25832.
                When ``None``, falls back to ``request_params.bbox``
                lower-left (reprojected from WGS84). When neither is
                given, no basepoint is written.
            basepoint_size: Edge length of the basepoint quad (meters).

        Returns:
            Path to the saved IFC file, or ``None`` on failure.
        """
        if not buildings:
            logger.error("No buildings to export.")
            return None

        try:
            model_builder = init_ifc_project(
                request_params=request_params,
                coordinate_system=coordinate_system,
                coordinate_operation=coordinate_operation,
            )
            model = model_builder.model
            model3d = context.add_context(model, context_type="Model")
            body = context.add_context(
                model,
                context_type="Model",
                context_identifier="Body",
                target_view="MODEL_VIEW",
                parent=model3d,
            )

            _add_building_elements(
                model=model,
                model_builder=model_builder,
                body=body,
                buildings=buildings,
                representation_color=representation_color,
                layer_name=layer_name,
                pset_hyperlink=pset_hyperlink,
            )

            place_basepoint(
                model=model,
                site=model_builder.site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=request_params.bbox_as_wgs84_tuple,
                size=basepoint_size,
            )

            saved_path = model_builder.save_ifc_to_output(output_name, output_path=output_path)
            if not saved_path:
                raise RuntimeError("Failed to save IFC file")
            return Path(str(saved_path))

        except Exception as e:
            logger.error(f"Failed to create IFC: {e}")
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
        representation_color: Tuple[float, float, float] = _DEFAULT_COLOR,
        layer_name: str = _DEFAULT_LAYER,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
    ) -> Optional[Path]:
        """One-shot: parse CityGML tiles, then build the IFC.

        The WGS84 bbox from ``request_params`` is used to crop the
        parser and — when no explicit ``basepoint_origin`` is given —
        as the fallback basepoint origin.
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
            representation_color=representation_color,
            layer_name=layer_name,
            pset_hyperlink=pset_hyperlink,
            basepoint_origin=basepoint_origin,
            basepoint_size=basepoint_size,
        )


# ---------------------------------------------------------------------------
# Module-level IFC writer helpers (private)
# ---------------------------------------------------------------------------


def _create_combined_representation(
    model,
    body_context,
    vertices: List[Tuple[float, float, float]],
    faces: List[List[int]],
    faces_with_voids: Optional[List[Dict[str, Any]]],
):
    """Create a polygonal face set from regular faces and faces-with-voids."""
    coord_list = [tuple(map(float, v)) for v in vertices]
    pt_list = model.create_entity("IfcCartesianPointList3D", CoordList=coord_list)

    ifc_faces = []

    if faces:
        for ring in faces:
            cleaned = clean_polygon_ring([i + 1 for i in ring])
            if len(cleaned) >= 3:
                ifc_faces.append(model.create_entity("IfcIndexedPolygonalFace", CoordIndex=cleaned))

    if faces_with_voids:
        for fs in faces_with_voids:
            parsed = parse_face_with_voids(fs, index_offset=1)
            if parsed is None:
                continue
            outer, inners = parsed
            if fs.get("type") == "IfcIndexedPolygonalFaceWithVoids":
                ifc_faces.append(
                    model.create_entity(
                        "IfcIndexedPolygonalFaceWithVoids",
                        CoordIndex=outer,
                        InnerCoordIndices=inners,
                    )
                )
            else:
                ifc_faces.append(
                    model.create_entity(
                        "IfcIndexedPolygonalFace",
                        CoordIndex=outer,
                    )
                )

    face_set = model.create_entity(
        "IfcPolygonalFaceSet",
        Coordinates=pt_list,
        Faces=ifc_faces,
        Closed=True,
    )

    return model.create_entity(
        "IfcShapeRepresentation",
        ContextOfItems=body_context,
        RepresentationIdentifier="Body",
        RepresentationType="Tessellation",
        Items=[face_set],
    )


def _add_building_elements(
    *,
    model,
    model_builder: IfcModelBuilder,
    body,
    buildings: List[Building],
    representation_color: Tuple[float, float, float],
    layer_name: str,
    pset_hyperlink: Optional[Pset_Hyperlink],
) -> None:
    """Append ``IfcBuildingElementProxy`` instances for every building record."""
    if pset_hyperlink is None:
        pset_hyperlink = default_bim_hamburg_hyperlink()

    identity = np.eye(4)
    representations = []

    # Short-circuit owner/user lookup during the bulk attribute edits (matches
    # the previous implementation; avoids an expensive per-attribute query).
    _orig_get_user = owner_settings.get_user
    _orig_get_app = owner_settings.get_application
    owner_settings.get_user = lambda *_: None
    owner_settings.get_application = lambda *_: None

    try:
        elements = [root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=b.id) for b in buildings]

        for element, building in zip(elements, buildings):
            pset_ifc = pset.add_pset(model, product=element, name="Pset_Objektinformation")
            pydantic_properties = building.attributes.to_dict_with_labels(by_alias=True)
            properties = {k: v for k, v in pydantic_properties.items() if v is not None}
            pset.edit_pset(model, pset=pset_ifc, properties=properties)

            pset_hyperlink_ifc = pset.add_pset(model, product=element, name="Pset_Hyperlink")
            pset.edit_pset(
                model,
                pset=pset_hyperlink_ifc,
                properties=pset_hyperlink.model_dump(by_alias=True),
            )

            if building.faces_with_voids:
                representation = _create_combined_representation(
                    model,
                    body,
                    building.vertices,
                    building.faces,
                    building.faces_with_voids,
                )
            else:
                representation = geometry.add_mesh_representation(
                    model,
                    context=body,
                    vertices=[building.vertices],
                    faces=[building.faces],
                    edges=[[]],
                )

            IfcSnippets.assign_color_to_representation(model, representation, representation_color, 0.0)
            representations.append(representation)
            geometry.assign_representation(model, product=element, representation=representation)

        spatial.assign_container(model, relating_structure=model_builder.building, products=elements)
        for element in elements:
            geometry.edit_object_placement(model, product=element, matrix=identity)
    finally:
        owner_settings.get_user = _orig_get_user
        owner_settings.get_application = _orig_get_app

    IfcSnippets.batch_assign_layer_to_representations(model, representations, layer_name, representation_color)


__all__ = ["CityBasicApp"]
