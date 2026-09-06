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
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from BIMFabrikHH_core.apps.trees.processing import resolve_tree_dimensions
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
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
    attrs: Dict[str, str] = {
        "name": record.name,
        "kronendurchmesser": str(record.kronendurchmesser),
        "stammdurchmesser": str(record.stammdurchmesser),
    }
    if record.baumhoehe is not None:
        attrs["baumhoehe"] = str(record.baumhoehe)
    for pset in record.psets.values():
        dump = pset.model_dump(mode="python") if hasattr(pset, "model_dump") else {}
        for key, value in dump.items():
            if key == "pset_name":
                continue
            text = _attr_value(value)
            if text is not None:
                attrs.setdefault(key, text)
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
        "trunk_height": dims.trunk_height,
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
        basepoint_origin: Optional[Tuple[float, float]] = None,
        project_name: str = "Trees_Generic_Project",
        site_name: str = "Trees_Generic_Site",
        epsg: int = 25832,
        psets=None,
        drape_vertices: Optional[Sequence[Sequence[float]]] = None,
        drape_faces: Optional[Sequence[Sequence[int]]] = None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write trees to IFC. Same ``TreeRecord`` list as :class:`TreesGenericApp`.

        ``psets`` defaults to ``tree_mapping.specs()``. Pass ``[]`` for none.
        Optional ``drape_vertices`` / ``drape_faces`` fill ``z = 0`` from a DGM mesh.
        """
        if not records:
            logger.error("TreesRustApp.build_ifc: no tree records.")
            return None
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
            epsg=epsg,
            psets=psets,
            basepoint=basepoint_origin,
            drape_vertices=drape_vertices,
            drape_faces=drape_faces,
            progress=progress,
        )
        logger.info("TreesRustApp wrote %s", written)
        return Path(written)
