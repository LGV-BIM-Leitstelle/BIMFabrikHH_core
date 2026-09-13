"""
Rust Terrain App
================

:class:`TerrainMesh` → IFC4 STEP via ``bimfabrikhh_core_rs``. Python still
samples / Delaunay (:func:`extract_mesh_adaptive`) and splits the guided TIN
into land-use parts (:func:`build_landuse_parts`); Rust only writes STEP.

Matches :class:`TerrainGenericApp` feature-for-feature: guided ALKIS
Bruchkanten, land-use splitting / parcel merging, water cutting, per-part
colours / layers / psets, and the optional LandXML sidecar. The heavy lifting
lives in the shared, writer-neutral helpers so both apps stay in lockstep.

Does not replace :class:`TerrainBasicApp` or :class:`TerrainGenericApp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from pydantic import BaseModel

from BIMFabrikHH_core.apps.terrain._ifc_common import (
    DEFAULT_TERRAIN_LAYER,
    RgbTuple,
    terrain_part_psets,
    terrain_part_style,
)
from BIMFabrikHH_core.apps.terrain.landxml import export_terrain_landxml
from BIMFabrikHH_core.apps.terrain.processing import (
    DEFAULT_GUIDE_EDGE_SPACING_M,
    build_landuse_parts,
    extract_mesh_adaptive,
    resolve_guide_records,
)
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.georeferencing import bbox_request_params_to_epsg25832
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_rust_app")

# Single-mesh colour is Rust ``TERRAIN_RGB`` (omit ``color``). Guided parts recolour per label.
_DEFAULT_TERRAIN_LAYER = DEFAULT_TERRAIN_LAYER
_DEFAULT_OUTPUT_NAME = "output_dgm_rust.ifc"
_MISSING_RS = (
    "TerrainRustApp needs bimfabrikhh_core_rs in this environment. "
    "Install with `pip install bimfabrikhh-core-rs`."
)


def _rust():
    try:
        from bimfabrikhh_core_rs import terrain_parts_to_ifc, terrain_to_ifc
        from bimfabrikhh_core_rs.terrain_mapping import specs as default_psets
    except ImportError as exc:  # pragma: no cover
        raise ImportError(_MISSING_RS) from exc
    return terrain_to_ifc, terrain_parts_to_ifc, default_psets


def _pset_to_wire(pset: BaseModel) -> Tuple[str, Dict[str, Any]]:
    """One Pydantic BIM.HH pset → ``(pset_name, {property: value})`` for Rust."""
    name = getattr(type(pset), "pset_name", type(pset).__name__)
    props = pset.model_dump(by_alias=True, exclude_none=True)
    return name, {str(k): v for k, v in props.items()}


def _psets_to_wire(psets: Optional[Sequence[BaseModel]]) -> Dict[str, Dict[str, Any]]:
    """A part's Pydantic psets → the ``{pset_name: {property: value}}`` Rust wants.

    Uses the exact same pset models as :class:`TerrainGenericApp` (via
    :func:`terrain_part_psets`), just serialized, so the written property sets
    are identical between the two writers.
    """
    wire: Dict[str, Dict[str, Any]] = {}
    for pset in psets or []:
        name, props = _pset_to_wire(pset)
        wire[name] = props
    return wire


class TerrainRustApp:
    """DGM export that delegates the IFC write to Rust."""

    @staticmethod
    def build_ifc(
        mesh: TerrainMesh,
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        name: str = "DGM",
        psets=None,
        epsg: int = 25832,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write a single prepared :class:`TerrainMesh` to IFC.

        ``psets`` defaults to ``terrain_mapping.specs()``. Pass ``[]`` for none.
        Basepoint XY is ``basepoint_origin``, else ``mesh.nullpunkt``, else
        the request bbox lower-left in EPSG:25832.
        Omit ``color`` to use Rust ``TERRAIN_RGB`` (102, 204, 0).
        """
        if mesh.is_empty():
            logger.warning("TerrainRustApp.build_ifc: empty mesh.")
            return None
        terrain_to_ifc, _, default_psets = _rust()
        dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if psets is None:
            psets = default_psets()
        project_name, site_name, _ = extract_project_info(request_params.containers)
        basepoint = TerrainRustApp._basepoint(basepoint_origin, request_params, mesh)
        extra: Dict[str, Any] = {}
        if color is not None:
            extra["color"] = color
        written = terrain_to_ifc(
            mesh.vertices,
            mesh.faces,
            str(dest),
            name=name,
            project_name=project_name or "DGM",
            site_name=site_name or "Hamburg_Site",
            epsg=epsg,
            psets=psets,
            basepoint=basepoint,
            layer=cad_layer,
            progress=progress,
            **extra,
        )
        logger.info("TerrainRustApp wrote %s", written)
        return Path(written)

    @staticmethod
    def build_parts_ifc(
        parts: Sequence[Tuple[str, TerrainMesh]],
        *,
        request_params: RequestParams,
        guide_records: Optional[Sequence[Any]] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        name: str = "DGM",
        psets: Optional[Sequence[BaseModel]] = None,
        epsg: int = 25832,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write ordered land-use ``(label, mesh)`` parts to one IFC via Rust.

        Each part becomes its own styled ``IfcBuildingElementProxy`` under the
        site, with the same colour, layer, element name and psets that
        :class:`TerrainGenericApp` assigns (shared via
        :func:`terrain_part_style` and :func:`terrain_part_psets`). ``psets``
        overrides the leftover ``DGM`` part's psets only.
        The leftover ``DGM`` part uses Rust ``TERRAIN_RGB`` unless ``color``
        is passed.
        """
        parts = [(label, m) for label, m in parts if not m.is_empty()]
        if not parts:
            logger.warning("TerrainRustApp.build_parts_ifc: no non-empty parts.")
            return None
        _, terrain_parts_to_ifc, _ = _rust()
        dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        project_name, site_name, _ = extract_project_info(request_params.containers)
        anchor = next((m for _, m in parts), None)
        basepoint = TerrainRustApp._basepoint(basepoint_origin, request_params, anchor)

        payload: List[Dict[str, Any]] = []
        style_fallback: RgbTuple = color if color is not None else (0, 0, 0)
        for label, part in parts:
            part_name, part_color, part_layer = terrain_part_style(
                label, color=style_fallback, cad_layer=cad_layer, name=name
            )
            part_psets = terrain_part_psets(label, guide_records, dgm_psets=psets)
            item: Dict[str, Any] = {
                "name": part_name,
                "vertices": part.vertices,
                "faces": part.faces,
                "layer": part_layer,
                "psets": _psets_to_wire(part_psets),
            }
            if label != "DGM" or color is not None:
                item["color"] = part_color
            payload.append(item)

        written = terrain_parts_to_ifc(
            payload,
            str(dest),
            project_name=project_name or "DGM",
            site_name=site_name or "Hamburg_Site",
            epsg=epsg,
            basepoint=basepoint,
            progress=progress,
        )
        logger.info("TerrainRustApp wrote %d part(s) → %s", len(payload), written)
        return Path(written)

    @classmethod
    def from_geotiffs(
        cls,
        tif_files: Iterable[Union[str, Path]],
        *,
        request_params: RequestParams,
        folder_path: Optional[Union[str, Path]] = None,
        min_points: int = 1000,
        importance_threshold: float = 0.1,
        move_to_origin: bool = False,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: Optional[RgbTuple] = None,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        psets: Optional[Sequence[BaseModel]] = None,
        epsg: int = 25832,
        progress: bool = False,
        guide_records: Optional[Sequence[Any]] = None,
        guide_edge_spacing_m: float = DEFAULT_GUIDE_EDGE_SPACING_M,
        merge_parcels: bool = True,
        split_by_landuse: bool = False,
        guide_from_oaf: bool = False,
        write_geojson: bool = False,
        export_landxml: bool = False,
        landxml_path: Optional[Union[str, Path]] = None,
    ) -> Optional[Path]:
        """One-shot: mesh GeoTIFFs, split by land use, then write IFC in Rust.

        Mirrors :meth:`TerrainGenericApp.from_geotiffs`. When ``guide_records``
        (or ``guide_from_oaf``) yield ALKIS ``Nutzung`` and ``merge_parcels`` /
        ``split_by_landuse`` is set, the guided TIN is split into land-use
        parts written as separate proxies; otherwise a single DGM mesh is
        written. ``export_landxml`` additionally writes a LandXML 1.2 TIN with
        one ``<Surface>`` per part.
        """
        guide_records = resolve_guide_records(
            guide_records,
            request_params.bbox_as_wgs84_tuple,
            guide_from_oaf=guide_from_oaf,
            write_geojson=write_geojson,
            output_dir=(Path(output_path).parent if output_path is not None else None),
        )

        bbox_utm = bbox_request_params_to_epsg25832(request_params)
        water_meshes: Dict[str, TerrainMesh] = {}
        mesh = extract_mesh_adaptive(
            tif_files,
            folder_path=folder_path,
            min_points=min_points,
            importance_threshold=importance_threshold,
            bbox_utm=bbox_utm,
            move_to_origin=move_to_origin,
            guide_records=guide_records,
            guide_edge_spacing_m=guide_edge_spacing_m,
            water_meshes=water_meshes,
        )
        labeled = build_landuse_parts(
            mesh,
            guide_records,
            bbox_utm=bbox_utm,
            water_meshes=water_meshes,
            spacing=guide_edge_spacing_m,
            split_by_landuse=split_by_landuse,
            merge_parcels=merge_parcels,
        )

        if labeled:
            result = cls.build_parts_ifc(
                labeled,
                request_params=request_params,
                guide_records=guide_records,
                output_path=output_path,
                output_name=output_name,
                basepoint_origin=basepoint_origin,
                color=color,
                cad_layer=cad_layer,
                psets=psets,
                epsg=epsg,
                progress=progress,
            )
        else:
            result = cls.build_ifc(
                mesh,
                request_params=request_params,
                output_path=output_path,
                output_name=output_name,
                basepoint_origin=basepoint_origin,
                color=color,
                cad_layer=cad_layer,
                psets=psets,
                epsg=epsg,
                progress=progress,
            )

        if export_landxml:
            surfaces: List[Tuple[str, TerrainMesh]] = list(labeled) if labeled else [("DGM", mesh)]
            export_terrain_landxml(result, surfaces, landxml_path=landxml_path, epsg=epsg)

        return result

    @staticmethod
    def _basepoint(
        basepoint_origin: Optional[Tuple[float, float]],
        request_params: RequestParams,
        mesh: Optional[TerrainMesh],
    ) -> Optional[Tuple[float, float]]:
        """Basepoint XY: explicit origin, else ``mesh.nullpunkt``, else bbox LL."""
        basepoint = basepoint_origin or (mesh.nullpunkt if mesh is not None else None)
        if basepoint is None:
            bbox_utm = bbox_request_params_to_epsg25832(request_params)
            if bbox_utm is not None:
                basepoint = (bbox_utm[0], bbox_utm[1])
        return basepoint


__all__ = ["TerrainRustApp"]
