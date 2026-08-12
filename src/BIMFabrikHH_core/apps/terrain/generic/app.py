"""
Generic Terrain App
===================

Build an IFC DGM from a :class:`TerrainMesh` using the ``ifcfactory``
``BIMFactoryElement`` pipeline. Mirrors the open-house tutorial terrain
pattern (``MeshRepresentation`` wrapped in ``Style``) and lets callers
attach Pydantic property-set templates (``Pset_Objektinformation_DGM``
+ ``Pset_Hyperlink`` by default).

Shares the pure meshing pipeline (``extract_mesh_adaptive``) and the
IFC-adjacent helpers (basepoint placement, bbox resolution, default
psets) with :class:`TerrainBasicApp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from ifcfactory import BIMFactoryElement, MeshRepresentation, Style
from pydantic import BaseModel

from BIMFabrikHH_core.apps.terrain._ifc_common import default_terrain_psets
from BIMFabrikHH_core.apps.terrain.processing import extract_mesh_adaptive
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.georeferencing import bbox_request_params_to_epsg25832
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import (
    extract_psets_basepoint,
)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import (
    Pset_Objektinformation_DGM,
)
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_generic_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_TERRAIN_RGB: RgbTuple = (102, 204, 0)
_DEFAULT_TERRAIN_LAYER: str = "_BIM_DGM_Gelaende"
_DEFAULT_OUTPUT_NAME: str = "output_dgm_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0


class TerrainGenericApp:
    """Record-builder terrain app built on ``ifcfactory``.

    ``build_ifc`` takes a prepared :class:`TerrainMesh` and writes the DGM
    as a single ``IfcBuildingElementProxy`` with a ``MeshRepresentation``
    styled via :class:`ifcfactory.Style`, then places the project
    basepoint quad. :meth:`from_geotiffs` combines mesh extraction and
    IFC building in one call.
    """

    @staticmethod
    def build_ifc(
        mesh: TerrainMesh,
        *,
        request_params: RequestParams,
        psets: Optional[Sequence[BaseModel]] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        name: str = "DGM",
        transparency: float = 0.0,
    ) -> Optional[Path]:
        """Build an IFC file from a prepared :class:`TerrainMesh`.

        Args:
            mesh: Triangulated terrain mesh in the project CRS (EPSG:25832).
            request_params: Project metadata and pset containers.
            psets: Pydantic pset models to attach to the DGM element.
                Defaults to :class:`Pset_Objektinformation_DGM` and
                :class:`Pset_Hyperlink` with their template defaults.
            output_path: Full path to write the IFC to. When ``None``,
                the file is written to ``PathConfig.OUTPUT / output_name``.
            output_name: Default filename when ``output_path`` is ``None``.
            basepoint_size: Edge length of the basepoint quad (meters).
            basepoint_origin: Explicit ``(x, y)`` origin in EPSG:25832 for
                the basepoint quad. When ``None``, placement uses the request
                WGS84 bbox lower-left (via :attr:`RequestParams.bbox_as_wgs84_tuple`)
                if ``bbox`` is set; otherwise no Nullpunktobjekt is written.
            color: RGB as ``(R, G, B)`` in 0-255 **or** normalized 0-1 floats.
            cad_layer: CAD layer name assigned to the terrain mesh.
            name: IFC element name for the DGM.
            transparency: 0.0 = opaque, 1.0 = fully transparent.

        Returns:
            Path to the saved IFC file, or ``None`` on failure.
        """
        if mesh.is_empty():
            logger.warning("No valid terrain data to convert.")
            return None

        try:
            logger.info(f"Creating IFC model with {len(mesh.vertices)} vertices and {len(mesh.faces)} faces...")

            builder = init_ifc_project(request_params=request_params, building_name="DGM")
            model = builder.model
            if model is None:
                logger.error("Failed to create IFC model")
                return None

            effective_psets = list(psets) if psets is not None else default_terrain_psets()
            dgm_element = _terrain_element_from_mesh(
                mesh=mesh,
                name=name,
                color=color,
                cad_layer=cad_layer,
                transparency=transparency,
                psets=effective_psets,
            )

            BIMFactoryElement.build_in(model, inst=builder.site, items=[dgm_element])

            place_basepoint(
                model=model,
                site=builder.site,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=(None if basepoint_origin is not None else request_params.bbox_as_wgs84_tuple),
                size=basepoint_size,
                psets=extract_psets_basepoint(request_params.containers or []),
            )

            logger.info("Saving IFC model...")
            return builder.save_ifc_to_output(output_name, output_path=output_path)

        except Exception as e:
            logger.error(f"Error creating IFC model: {e}")
            import traceback

            traceback.print_exc()
            return None

    @classmethod
    def from_geotiffs(
        cls,
        tif_files: Iterable[Union[str, Path]],
        *,
        request_params: RequestParams,
        psets: Optional[Sequence[BaseModel]] = None,
        folder_path: Optional[Union[str, Path]] = None,
        min_points: int = 1000,
        importance_threshold: float = 0.1,
        move_to_origin: bool = False,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
    ) -> Optional[Path]:
        """One-shot: extract a mesh from GeoTIFFs, then build the IFC.

        Combines :func:`extract_mesh_adaptive` and :meth:`build_ifc`.
        The bbox from ``request_params`` (WGS84) is projected to
        EPSG:25832 before extraction.
        """
        bbox_utm = bbox_request_params_to_epsg25832(request_params)
        mesh = extract_mesh_adaptive(
            tif_files,
            folder_path=folder_path,
            min_points=min_points,
            importance_threshold=importance_threshold,
            bbox_utm=bbox_utm,
            move_to_origin=move_to_origin,
        )
        return cls.build_ifc(
            mesh,
            request_params=request_params,
            psets=psets,
            output_path=output_path,
            output_name=output_name,
            basepoint_size=basepoint_size,
            basepoint_origin=basepoint_origin,
            color=color,
            cad_layer=cad_layer,
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _terrain_element_from_mesh(
    *,
    mesh: TerrainMesh,
    name: str,
    color: RgbTuple,
    cad_layer: str,
    transparency: float,
    psets: List[BaseModel],
) -> BIMFactoryElement:
    """Wrap the terrain mesh in a styled ``BIMFactoryElement`` ready for ``build_in``."""
    vertices: List[Tuple[float, float, float]] = [(float(v[0]), float(v[1]), float(v[2])) for v in mesh.vertices]

    mesh_item = MeshRepresentation(vertices=vertices, faces=mesh.faces)
    styled_mesh = Style(
        item=mesh_item,
        rgb=color,
        transparency=transparency,
        cad_layer=cad_layer,
    )

    return BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name=name,
        qsets=False,
        children=[styled_mesh],
        psets=psets,
    )


__all__ = ["TerrainGenericApp", "Pset_Objektinformation_DGM"]
