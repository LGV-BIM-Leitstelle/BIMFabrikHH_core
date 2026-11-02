"""
Rust Boreholes App
==================

``list[BoreholeRecord]`` → IFC4 STEP via ``bimfabrikhh_core_rs.boreholes_to_ifc``.
Python still parses BoreholeML and resolves the code lists. Rust groups the
solids of one borehole into an ``IfcElementAssembly`` and writes STEP.

Does not replace :class:`BoreholesGenericApp`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.geometry import basepoint_pset_values, basepoint_xyz
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer, warn_if_degree_coordinates
from BIMFabrikHH_core.core.model_creator import output_coordinate_system, psets_to_wire
from BIMFabrikHH_core.data_models.boreholes import (
    BoreholeLayer,
    BoreholeRecord,
    collect_borehole_psets,
    collect_groundwater_psets,
)
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Hyperlink

logger = get_logger("boreholes_rust_app")

_DEFAULT_OUTPUT_NAME = "output_boreholes_rust.ifc"
_DEFAULT_LAYER_PREFIX = "_Bodenaufschluesse"
_DEFAULT_CYLINDER_RADIUS_M = 0.5
_DEFAULT_WATER_SQUARE_LENGTH = 3.0
_DEFAULT_BASEPOINT_SIZE = 8.0
_MISSING_RS = (
    "BoreholesRustApp needs bimfabrikhh_core_rs in this environment. "
    "Install with `pip install bimfabrikhh-core-rs`."
)

RgbTuple = Union[Tuple[float, float, float], Tuple[int, int, int]]


def _rust():
    try:
        from bimfabrikhh_core_rs import boreholes_to_ifc
    except ImportError as exc:  # pragma: no cover
        raise ImportError(_MISSING_RS) from exc
    return boreholes_to_ifc


def _cad_layer_name(din_color_name: str) -> str:
    """CAD layer per DIN colour, e.g. ``_Bodenaufschluesse_orange``. Same as the generic app."""
    return f"{_DEFAULT_LAYER_PREFIX}_{din_color_name.replace(' ', '_').lower()}"


def _element_name(record: BoreholeRecord, layer: BoreholeLayer) -> str:
    """``<Aufschlussbezeichnung>_<Bohrung>_<Nr>``. Same as the generic app."""
    return f"{record.aufschlussbezeichnung}_{layer.layer_id}".replace(" ", "_")[:120]


def _element_name_groundwater(record: BoreholeRecord) -> str:
    """``<Aufschlussbezeichnung>_<Bohrung>_Grundwasser``. Same as the generic app."""
    return f"{record.aufschlussbezeichnung}_{record.borehole_id}_Grundwasser".replace(" ", "_")[:120]


def _borehole_name(record: BoreholeRecord) -> str:
    name = (record.aufschlussbezeichnung or "").strip()
    return name or record.borehole_id


def _wire_psets(psets: List[Any], hyperlink_override: Optional[Pset_Hyperlink]) -> Dict[str, Dict[str, Any]]:
    if hyperlink_override is not None:
        psets = [pset for pset in psets if not isinstance(pset, Pset_Hyperlink)]
        psets.append(hyperlink_override)
    return psets_to_wire(psets)


def _solids(
    records: List[BoreholeRecord],
    *,
    cylinder_radius_m: float,
    water_square_length: float,
    color: Optional[RgbTuple],
    transparency: float,
    include_property_sets: bool,
    hyperlink_override: Optional[Pset_Hyperlink],
) -> List[dict]:
    solids: List[dict] = []
    for record in records:
        borehole = record.borehole_id
        borehole_name = _borehole_name(record)
        for layer in record.layers:
            solids.append(
                {
                    "borehole": borehole,
                    "borehole_name": borehole_name,
                    "name": _element_name(record, layer),
                    "position": (record.easting, record.northing, layer.lower_height),
                    "height": layer.thickness,
                    "radius": cylinder_radius_m,
                    "color": color if color is not None else layer.visual_rgb,
                    "transparency": transparency,
                    "layer": _cad_layer_name(layer.din_color_name),
                    "psets": _wire_psets(
                        collect_borehole_psets(record, layer, include_property_sets=include_property_sets),
                        hyperlink_override,
                    ),
                }
            )
        water = record.groundwater
        if water is not None and water.entry_depth is not None:
            solids.append(
                {
                    "borehole": borehole,
                    "borehole_name": borehole_name,
                    "name": _element_name_groundwater(record),
                    "kind": "square",
                    "position": (record.easting, record.northing, record.ansatzhoehe_nn - water.entry_depth),
                    "size": water_square_length,
                    "psets": _wire_psets(
                        collect_groundwater_psets(record, include_property_sets=include_property_sets),
                        hyperlink_override,
                    ),
                }
            )
    return solids


class BoreholesRustApp:
    """Borehole export that delegates the solids and the IFC write to Rust."""

    @staticmethod
    def build_ifc(
        records: List[BoreholeRecord],
        *,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        include_property_sets: bool = True,
        cylinder_radius_m: float = _DEFAULT_CYLINDER_RADIUS_M,
        water_square_length: float = _DEFAULT_WATER_SQUARE_LENGTH,
        color: Optional[RgbTuple] = None,
        transparency: float = 0.0,
        pset_hyperlink: Optional[Pset_Hyperlink] = None,
        basepoint: Optional[Tuple[float, float, float]] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
        basepoint_psets: Optional[Dict[str, Any]] = None,
        bbox_wgs84: Optional[Tuple[float, float, float, float]] = None,
        project_name: str = "Boreholes_Generic_Project",
        site_name: str = "Boreholes_Generic_Site",
        source_epsg: Optional[int] = None,
        output_epsg: Optional[int] = None,
        vertical_epsg: Optional[int] = None,
        progress: bool = False,
    ) -> Optional[Path]:
        """Write boreholes to IFC. Same ``BoreholeRecord`` list as :class:`BoreholesGenericApp`.

        Each soil layer becomes a cylinder standing on its lower edge, and a
        groundwater entry becomes a square at the water level. Solids that share
        a borehole id become one ``IfcElementAssembly`` (object type ``Bohrung``).
        There is no ``IfcMaterial``: colour and transparency are written on
        ``IfcSurfaceStyleShading``.

        ``source_epsg`` / ``output_epsg`` / ``vertical_epsg`` work as in
        :meth:`BoreholesGenericApp.build_ifc`: positions and ``basepoint_origin``
        are in ``source_epsg`` and are transformed into ``output_epsg`` when
        given. The basepoint is ``basepoint`` (XYZ in the output CRS), else
        ``basepoint_origin``, else the ``bbox_wgs84`` lower-left at height 0,
        else none. ``basepoint_size`` is its edge length.
        """
        if not records:
            logger.error("BoreholesRustApp.build_ifc: no borehole records.")
            return None
        transformer = CoordinateTransformer.from_source_to_output(source_epsg, output_epsg, vertical_epsg)
        warn_if_degree_coordinates(((record.easting, record.northing) for record in records), transformer)
        if transformer is not None and not transformer.is_identity:
            xs, ys = transformer.transform_xy_batch(
                [record.easting for record in records], [record.northing for record in records]
            )
            records = [
                record.model_copy(update={"easting": x, "northing": y}) for record, x, y in zip(records, xs, ys)
            ]
        solids = _solids(
            records,
            cylinder_radius_m=cylinder_radius_m,
            water_square_length=water_square_length,
            color=color,
            transparency=transparency,
            include_property_sets=include_property_sets,
            hyperlink_override=pset_hyperlink,
        )
        if not any(solid.get("kind", "cylinder") == "cylinder" for solid in solids):
            logger.error("BoreholesRustApp.build_ifc: no layers found on the given borehole records.")
            return None

        boreholes_to_ifc = _rust()
        dest = Path(output_path) if output_path is not None else PathConfig.OUTPUT / output_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        basepoint = basepoint_xyz(
            basepoint=basepoint,
            basepoint_origin=basepoint_origin,
            bbox_wgs84=bbox_wgs84 if transformer is not None else None,
            transformer=transformer,
        )
        written = boreholes_to_ifc(
            solids,
            str(dest),
            project_name=project_name,
            site_name=site_name,
            crs=output_coordinate_system(transformer),
            basepoint=basepoint,
            basepoint_size=basepoint_size,
            basepoint_psets=basepoint_pset_values(basepoint_psets),
            progress=progress,
        )
        logger.info("BoreholesRustApp wrote %s", written)
        return Path(written)
