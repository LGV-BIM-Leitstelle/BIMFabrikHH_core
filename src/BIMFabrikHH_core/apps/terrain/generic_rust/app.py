"""
Rust Terrain App
================

:class:`TerrainMesh` → IFC4 STEP via ``bimfabrikhh_core_rs.terrain_to_ifc``.
Python still samples / Delaunay (:func:`extract_mesh_adaptive`).
Rust only writes STEP.

Does not replace :class:`TerrainBasicApp` or :class:`TerrainGenericApp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple, Union

from BIMFabrikHH_core.apps.terrain.processing import extract_mesh_adaptive
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.georeferencing import bbox_request_params_to_epsg25832
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_rust_app")

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]

_DEFAULT_TERRAIN_RGB: RgbTuple = (102, 204, 0)
_DEFAULT_TERRAIN_LAYER = "_BIM_DGM_Gelaende"
_DEFAULT_OUTPUT_NAME = "output_dgm_rust.ifc"
_MISSING_RS = (
    "TerrainRustApp needs bimfabrikhh_core_rs in this environment. "
    "Install with `pip install bimfabrikhh-core-rs`."
)


def _rust():
    try:
        from bimfabrikhh_core_rs import terrain_to_ifc
        from bimfabrikhh_core_rs.terrain_mapping import specs as default_psets
    except ImportError as exc:  # pragma: no cover
        raise ImportError(_MISSING_RS) from exc
    return terrain_to_ifc, default_psets


class TerrainRustApp:
    """DGM export that delegates IFC write to Rust."""

    @staticmethod
    def build_ifc(
        mesh: TerrainMesh,
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        name: str = "DGM",
        psets=None,
        epsg: int = 25832,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write a prepared :class:`TerrainMesh` to IFC.

        ``psets`` defaults to ``terrain_mapping.specs()``. Pass ``[]`` for none.
        Basepoint XY is ``basepoint_origin``, else ``mesh.nullpunkt``, else
        the request bbox lower-left in EPSG:25832.
        """
        if mesh.is_empty():
            logger.warning("TerrainRustApp.build_ifc: empty mesh.")
            return None
        terrain_to_ifc, default_psets = _rust()
        dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if psets is None:
            psets = default_psets()
        project_name, site_name, _ = extract_project_info(request_params.containers)
        basepoint = basepoint_origin or mesh.nullpunkt
        if basepoint is None:
            bbox_utm = bbox_request_params_to_epsg25832(request_params)
            if bbox_utm is not None:
                basepoint = (bbox_utm[0], bbox_utm[1])
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
            color=color,
            layer=cad_layer,
            progress=progress,
        )
        logger.info("TerrainRustApp wrote %s", written)
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
        color: RgbTuple = _DEFAULT_TERRAIN_RGB,
        cad_layer: str = _DEFAULT_TERRAIN_LAYER,
        psets=None,
        epsg: int = 25832,
        progress: bool = False,
    ) -> Optional[Path]:
        """Mesh GeoTIFFs with :func:`extract_mesh_adaptive`, then write IFC in Rust."""
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
            output_path=output_path,
            output_name=output_name,
            basepoint_origin=basepoint_origin,
            color=color,
            cad_layer=cad_layer,
            psets=psets,
            epsg=epsg,
            progress=progress,
        )
