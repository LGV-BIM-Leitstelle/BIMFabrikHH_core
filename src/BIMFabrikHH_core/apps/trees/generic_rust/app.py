"""
Rust Trees App
==============

``list[TreeRecord]`` → IFC4 STEP via ``bimfabrikhh_core_rs.trees_to_ifc``.
Python still prepares records (same contract as :class:`TreesGenericApp`).
Rust meshes trunk + crown and writes STEP.

Does not replace :class:`TreesBasicApp` or :class:`TreesGenericApp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from BIMFabrikHH_core.apps.trees.processing import (
    check_positions_in_dgm_crs,
    drape_records_on_dgm,
    resolve_tree_dimensions,
    transform_record_positions,
)
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.geometry import basepoint_pset_values, basepoint_xyz
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer, warn_if_degree_coordinates
from BIMFabrikHH_core.core.model_creator import output_coordinate_system
from BIMFabrikHH_core.data_models import TreeRecord

logger = get_logger("trees_rust_app")

_DEFAULT_OUTPUT_NAME = "output_trees_rust.ifc"
_MISSING_RS = (
    "TreesRustApp needs bimfabrikhh_core_rs in this environment. "
    "Install with `pip install bimfabrikhh-core-rs`."
)


def _rust():
    try:
        from bimfabrikhh_core_rs import trees_to_ifc
        from bimfabrikhh_core_rs.tree_mapping import specs as default_psets
    except ImportError as exc:  # pragma: no cover
        raise ImportError(_MISSING_RS) from exc
    return trees_to_ifc, default_psets


def _attr_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    magnitude = getattr(value, "magnitude", None)
    if magnitude is not None:
        value = magnitude
    text = str(value).strip()
    return text or None


def _attributes(record: TreeRecord) -> Dict[str, str]:
    """Flatten psets + record fields into the Rust writer's attribute dict.

    Psets are read first because they carry the published figures: ``baumhoehe``
    there is the Gesamthöhe, while ``record.baumhoehe`` is only the Stammhöhe
    that drives the geometry. The record then fills whatever a pset left out.
    """
    attrs: Dict[str, str] = {"name": record.name}
    for pset in record.psets.values():
        dump = pset.model_dump(mode="python") if hasattr(pset, "model_dump") else {}
        for key, value in dump.items():
            if key == "pset_name":
                continue
            text = _attr_value(value)
            if text is not None:
                attrs.setdefault(key, text)
    attrs.setdefault("kronendurchmesser", str(record.kronendurchmesser))
    attrs.setdefault("stammdurchmesser", str(record.stammdurchmesser))
    if record.baumhoehe is not None:
        attrs.setdefault("baumhoehe", str(record.baumhoehe))
    return attrs


def _tree_dict(
    record: TreeRecord,
    *,
    name_prefix: str,
    trunk_color: Tuple[float, ...],
    crown_color: Tuple[float, ...],
) -> dict:
    dims = resolve_tree_dimensions(record)
    name = record.name or "Baum"
    if name_prefix:
        name = f"{name_prefix}{name}"
    return {
        "name": name,
        "position": tuple(float(v) for v in record.position),
        "trunk_radius": dims.trunk_radius,
        "trunk_height": dims.trunk_cylinder_height,
        "crown_radius": dims.crown_radius,
        "detail": int(record.detail),
        "segments": int(record.segments),
        "is_stump": bool(record.is_stump),
        "trunk_color": trunk_color,
        "crown_color": crown_color,
        "attributes": _attributes(record),
    }


class TreesRustApp:
    """Tree export that delegates mesh + IFC write to Rust."""

    @staticmethod
    def build_ifc(
        records: List[TreeRecord],
        *,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        include_property_sets: bool = True,
        trunk_color: Tuple[float, ...] = (112, 69, 46),
        crown_color: Tuple[float, ...] = (33, 128, 46),
        name_prefix: str = "",
        basepoint: Optional[Tuple[float, float, float]] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = 1.0,
        basepoint_psets: Optional[Dict[str, Any]] = None,
        bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
        project_name: str = "Trees_Generic_Project",
        site_name: str = "Trees_Generic_Site",
        source_epsg: Optional[int] = None,
        output_epsg: Optional[int] = None,
        vertical_epsg: Optional[int] = None,
        psets=None,
        tif_files: Optional[Iterable[Union[str, Path]]] = None,
        dgm_folder: Optional[Union[str, Path]] = None,
        default_elevation: float = 0.0,
        drape_vertices: Optional[Sequence[Sequence[float]]] = None,
        drape_faces: Optional[Sequence[Sequence[int]]] = None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write trees to IFC. Same ``TreeRecord`` list as :class:`TreesGenericApp`.

        ``psets`` defaults to ``tree_mapping.specs()``. Pass ``[]`` for none.
        ``tif_files`` / ``dgm_folder`` sample each tree's Z from DGM GeoTIFF
        tiles (same contract as :meth:`TreesGenericApp.build_ifc`). Optional
        ``drape_vertices`` / ``drape_faces`` instead fill ``z = 0`` from a DGM mesh.
        Basepoint is ``basepoint`` (XYZ in the output CRS), else ``basepoint_origin``,
        else the ``bbox_wgs84`` lower-left (only with a known CRS), the last two at
        height 0, else none. ``basepoint_size`` is its edge length, as in
        :meth:`TreesGenericApp.build_ifc`. ``basepoint_psets`` is the
        :func:`extract_psets_basepoint` payload, as for
        :meth:`TreesGenericApp.build_ifc`; omit it and the Nullpunktobjekt gets only the
        fixed ``Pset_Objektinformation`` and ``Pset_Hyperlink``.

        ``source_epsg`` / ``output_epsg`` / ``vertical_epsg`` work as in
        :meth:`TreesGenericApp.build_ifc`: positions and ``basepoint_origin`` are
        in ``source_epsg`` and are transformed into ``output_epsg`` when given;
        Rust writes the resulting CRS and height system into the IFC header.
        Without ``source_epsg`` the positions are written as they are and the
        IFC gets no georeferencing.
        """
        if not records:
            logger.error("TreesRustApp.build_ifc: no tree records.")
            return None
        transformer = CoordinateTransformer.from_source_to_output(source_epsg, output_epsg, vertical_epsg)
        warn_if_degree_coordinates((r.position for r in records), transformer)
        if tif_files is not None:
            check_positions_in_dgm_crs(transformer)
            records = drape_records_on_dgm(
                records,
                tif_files,
                folder_path=dgm_folder,
                default_elevation=default_elevation,
            )
        if drape_vertices is not None and transformer is not None and not transformer.is_identity:
            raise ValueError("drape_vertices needs the DGM mesh in the output CRS; drape with tif_files instead")
        records = transform_record_positions(records, transformer)
        basepoint = basepoint_xyz(
            basepoint=basepoint,
            basepoint_origin=basepoint_origin,
            bbox_wgs84=bbox_wgs84 if transformer is not None else None,
            transformer=transformer,
        )
        trees_to_ifc, default_psets = _rust()
        dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if psets is None and include_property_sets:
            psets = default_psets()
        elif not include_property_sets:
            psets = []
        trees = [
            _tree_dict(record, name_prefix=name_prefix, trunk_color=trunk_color, crown_color=crown_color)
            for record in records
        ]
        written = trees_to_ifc(
            trees,
            str(dest),
            project_name=project_name,
            site_name=site_name,
            crs=output_coordinate_system(transformer),
            psets=psets,
            basepoint=basepoint,
            basepoint_size=basepoint_size,
            basepoint_psets=basepoint_pset_values(basepoint_psets),
            drape_vertices=drape_vertices,
            drape_faces=drape_faces,
            progress=progress,
        )
        logger.info("TreesRustApp wrote %s", written)
        return Path(written)
