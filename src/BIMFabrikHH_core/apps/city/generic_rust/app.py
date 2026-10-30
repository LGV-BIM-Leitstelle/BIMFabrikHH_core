"""
Rust City Model App
===================

One-shot CityGML (or CityJSON) → IFC4 STEP via ``bimfabrikhh_core_rs``.
Geometry stays in Rust. There is no ``build_ifc(buildings)`` — pass file
paths (or CityJSON text) and get an IFC path back.

``mode="mesh"`` is one ``IfcBuildingElementProxy`` per building
(:class:`CityGenericApp`). ``mode="typed"`` is one product per surface
(:class:`CityGenericEntityApp`).

EPSG handling matches :class:`CityGenericApp`: the tiles are in
``request_params.source_epsg`` and are transformed into
``request_params.output_epsg`` when given. Rust has no PROJ, so the pyproj
transformation is passed to Rust as ``transform`` and called once with all
coordinates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Tuple, Union

from BIMFabrikHH_core.apps.city.processing import bbox_in_source_crs, with_tile_crs
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.geometry import basepoint_pset_values, basepoint_xy
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer
from BIMFabrikHH_core.core.model_creator import output_coordinate_system
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info, extract_psets_basepoint
from BIMFabrikHH_core.data_models.params_tree import RequestParams

logger = get_logger("city_rust_app")

_DEFAULT_OUTPUT_NAME = "output_citymodel_rust.ifc"
#: Same as CityGenericApp.
_DEFAULT_BASEPOINT_SIZE: float = 8.0
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
        color: Optional[Tuple[float, float, float]] = None,
        cad_layer: bool = True,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
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

        A ``request_params.bbox`` crops the tiles in ``source_epsg`` (it needs
        one); the basepoint is ``basepoint_origin`` (in ``source_epsg``), else
        the bbox lower-left, both in the output CRS; ``basepoint_size`` is its
        edge length, as in :class:`CityGenericApp`. Without ``source_epsg``
        the coordinates are written as they are, without georeferencing. An
        empty ``source_epsg`` / ``vertical_epsg`` is taken from the ``srsName``
        of the tiles, and a contradicting one raises (see :func:`with_tile_crs`).
        """
        del folder_path
        paths = [str(p) for p in gml_files]
        if not paths:
            logger.error("CityRustApp.from_gml_files: no GML files.")
            return None
        request_params = with_tile_crs(request_params, paths)
        dest = _resolve_output(output_path, output_name)
        gml_to_ifc, _, _, _ = _rust()
        written = gml_to_ifc(
            paths,
            str(dest),
            building_id_filter=building_id_filter,
            **_export_kwargs(
                request_params,
                mode=mode,
                color=color,
                cad_layer=cad_layer,
                basepoint_origin=basepoint_origin,
                basepoint_size=basepoint_size,
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
        color: Optional[Tuple[float, float, float]] = None,
        cad_layer: bool = True,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        psets=None,
        ifc_types=None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Parse CityJSON (path, paths, or document text) and write one IFC.

        Options and EPSG handling as in :meth:`from_gml_files`.
        """
        dest = _resolve_output(output_path, output_name)
        _, cityjson_to_ifc, _, _ = _rust()
        written = cityjson_to_ifc(
            source,
            str(dest),
            building_id_filter=building_id_filter,
            **_export_kwargs(
                request_params,
                mode=mode,
                color=color,
                cad_layer=cad_layer,
                basepoint_origin=basepoint_origin,
                basepoint_size=basepoint_size,
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


def _export_kwargs(
    request_params: RequestParams,
    *,
    mode: str,
    color: Optional[Tuple[float, float, float]],
    cad_layer: bool,
    basepoint_origin: Optional[Tuple[float, float]],
    basepoint_size: float,
    psets,
    ifc_types,
    progress: bool,
) -> dict:
    project_name, site_name, _ = extract_project_info(request_params.containers)
    transformer = CoordinateTransformer.from_source_to_output(
        request_params.source_epsg, request_params.output_epsg, request_params.vertical_epsg
    )
    bbox_wgs84 = request_params.bbox_as_wgs84_tuple
    bbox_epsg = bbox_in_source_crs(bbox_wgs84, request_params.source_epsg)
    basepoint = basepoint_xy(
        basepoint_origin=basepoint_origin,
        bbox_wgs84=bbox_wgs84 if transformer is not None else None,
        transformer=transformer,
    )
    transform = None
    if transformer is not None and not transformer.is_identity:
        transform = transformer.transformer.transform
    _, _, default_psets, hamburg_ifc_types = _rust()
    if psets is None:
        psets = default_psets()
    if ifc_types is None and mode.lower() == "typed":
        ifc_types = hamburg_ifc_types()
    kwargs = {
        "mode": mode,
        "project_name": project_name,
        "site_name": site_name,
        "crs": output_coordinate_system(transformer),
        "bbox_epsg": bbox_epsg,
        "transform": transform,
        "basepoint": basepoint,
        "basepoint_size": basepoint_size,
        "basepoint_psets": basepoint_pset_values(extract_psets_basepoint(request_params.containers or [])),
        "psets": psets,
        "ifc_types": ifc_types,
        "cad_layer": bool(cad_layer),
        "progress": progress,
    }
    if color is not None:
        kwargs["colors"] = color
    return kwargs
