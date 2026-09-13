"""
Rust City Model App
===================

One-shot CityGML (or CityJSON) → IFC4 STEP via ``bimfabrikhh_core_rs``.
Geometry stays in Rust. There is no ``build_ifc(buildings)`` — pass file
paths (or CityJSON text) and get an IFC path back.

``mode="mesh"`` is one ``IfcBuildingElementProxy`` per building
(:class:`CityGenericApp`). ``mode="typed"`` is one product per surface
(:class:`CityGenericEntityApp`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from pyproj import Transformer

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateSystem,
    CoordinateSystemTemplates,
)

logger = get_logger("city_rust_app")

_DEFAULT_OUTPUT_NAME = "output_citymodel_rust.ifc"
_MISSING_RS = (
    "CityRustApp needs bimfabrikhh_core_rs in this environment. "
    "From the rust repo: source the BIMFabrik venv, then "
    "`maturin develop --release`."
)


def _rust():
    try:
        from bimfabrikhh_core_rs import cityjson_to_ifc, gml_to_ifc
        from bimfabrikhh_core_rs.attribute_mapping import specs as default_psets
        from bimfabrikhh_core_rs.ifc_types import hamburg_ifc_types
    except ImportError as exc:  # pragma: no cover
        raise ImportError(_MISSING_RS) from exc
    return gml_to_ifc, cityjson_to_ifc, default_psets, hamburg_ifc_types


class CityRustApp:
    """City-model export that delegates parse + IFC write to Rust."""

    @staticmethod
    def from_gml_files(
        gml_files: Sequence[Union[str, Path]],
        *,
        request_params: RequestParams,
        folder_path: Optional[Union[str, Path]] = None,
        mode: str = "mesh",
        building_id_filter: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        color: Optional[Tuple[float, float, float]] = None,
        cad_layer: bool = True,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        psets=None,
        ifc_types=None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Parse CityGML tiles and write one IFC.

        ``psets`` defaults to ``attribute_mapping.specs()`` (no quantities).
        Pass ``specs(quantities=True)`` for ``BIMFabrikHH_Quantities``, or
        ``[]`` for no property sets. ``ifc_types`` defaults to
        ``hamburg_ifc_types()`` when ``mode="typed"``. ``folder_path`` is
        accepted for :class:`CityGenericApp` call-site compatibility and is unused.
        """
        del folder_path
        paths = [str(p) for p in gml_files]
        if not paths:
            logger.error("CityRustApp.from_gml_files: no GML files.")
            return None
        dest = _resolve_output(output_path, output_name)
        gml_to_ifc, _, _, _ = _rust()
        written = gml_to_ifc(
            paths,
            str(dest),
            building_id_filter=building_id_filter,
            **_export_kwargs(
                request_params,
                mode=mode,
                coordinate_system=coordinate_system,
                color=color,
                cad_layer=cad_layer,
                basepoint_origin=basepoint_origin,
                psets=psets,
                ifc_types=ifc_types,
                progress=progress,
            ),
        )
        logger.info("CityRustApp wrote %s", written)
        return Path(written)

    @staticmethod
    def from_cityjson(
        source: Union[str, Sequence[str]],
        *,
        request_params: RequestParams,
        mode: str = "mesh",
        building_id_filter: Optional[str] = None,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_system: Optional[CoordinateSystem] = None,
        color: Optional[Tuple[float, float, float]] = None,
        cad_layer: bool = True,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        psets=None,
        ifc_types=None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Parse CityJSON (path, paths, or document text) and write one IFC."""
        dest = _resolve_output(output_path, output_name)
        _, cityjson_to_ifc, _, _ = _rust()
        written = cityjson_to_ifc(
            source,
            str(dest),
            building_id_filter=building_id_filter,
            **_export_kwargs(
                request_params,
                mode=mode,
                coordinate_system=coordinate_system,
                color=color,
                cad_layer=cad_layer,
                basepoint_origin=basepoint_origin,
                psets=psets,
                ifc_types=ifc_types,
                progress=progress,
            ),
        )
        logger.info("CityRustApp wrote %s", written)
        return Path(written)


def _resolve_output(output_path: Optional[Union[str, Path]], output_name: str) -> Path:
    dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def _epsg(coordinate_system: Optional[CoordinateSystem]) -> int:
    name = (coordinate_system or CoordinateSystemTemplates.epsg_25832()).name
    if name.upper().startswith("EPSG:"):
        return int(name.split(":", 1)[1])
    return 25832


def _bbox_epsg(request_params: RequestParams, epsg: int) -> Optional[Tuple[float, float, float, float]]:
    wgs = request_params.bbox_as_wgs84_tuple
    if wgs is None:
        return None
    transformer = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    x1, y1 = transformer.transform(wgs[0], wgs[1])
    x2, y2 = transformer.transform(wgs[2], wgs[3])
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def _export_kwargs(
    request_params: RequestParams,
    *,
    mode: str,
    coordinate_system: Optional[CoordinateSystem],
    color: Optional[Tuple[float, float, float]],
    cad_layer: bool,
    basepoint_origin: Optional[Tuple[float, float]],
    psets,
    ifc_types,
    progress: bool,
) -> dict:
    project_name, site_name, _ = extract_project_info(request_params.containers)
    epsg = _epsg(coordinate_system)
    bbox_epsg = _bbox_epsg(request_params, epsg)
    basepoint = basepoint_origin
    if basepoint is None and bbox_epsg is not None:
        basepoint = (bbox_epsg[0], bbox_epsg[1])
    _, _, default_psets, hamburg_ifc_types = _rust()
    if psets is None:
        psets = default_psets()
    if ifc_types is None and mode.lower() == "typed":
        ifc_types = hamburg_ifc_types()
    kwargs = {
        "mode": mode,
        "project_name": project_name,
        "site_name": site_name,
        "epsg": epsg,
        "bbox_epsg": bbox_epsg,
        "basepoint": basepoint,
        "psets": psets,
        "ifc_types": ifc_types,
        "cad_layer": bool(cad_layer),
        "progress": progress,
    }
    if color is not None:
        kwargs["colors"] = color
    return kwargs
