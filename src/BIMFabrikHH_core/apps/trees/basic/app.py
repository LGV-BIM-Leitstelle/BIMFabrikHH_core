"""
Basic Trees App
===============

Record-builder app: ``list[TreeRecord] -> IFC path``.

Builds an IFC tree model using ``ifcopenshell.api`` with mesh-based
cylindrical trunks and icosphere crowns. Property sets are attached as
``IfcRealProperty`` values from the Pydantic templates stored on each
:class:`TreeRecord`.

Scope of this module
--------------------

This file contains **only IFC-writing logic** for the mesh/icosphere
modelling choice. All data-processing logic (dimension math, pset
filtering, DataFrame parsing, height rules, column mapping, domain
validation) lives in :mod:`BIMFabrikHH_core.apps.trees.processing` and
is shared with :class:`TreesGenericApp`.

The app follows the same shape as ``TreesGenericApp``:

* A small class :class:`TreesBasicApp` with a single static
  :meth:`build_ifc` entry point.
* Module-level ``_private`` helpers that do the actual IFC writes.

The app satisfies the structural
:class:`BIMFabrikHH_core.apps.interface.RecordBuilderApp` protocol.

Copyright (C) 2025 Freie und Hansestadt Hamburg, Landesbetrieb
Geoinformation und Vermessung BIM-Leitstelle,
Ahmed Salem <ahmed.salem@gv.hamburg.de>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import ifcopenshell.api.geometry as ifc_geometry
import numpy as np
from icosphere import icosphere
from ifcopenshell.api import aggregate, pset, root, run, spatial
from ifcopenshell.util import placement
from pydantic import BaseModel

from BIMFabrikHH_core.apps.trees.processing import (
    TreeDimensions,
    collect_pydantic_psets,
    resolve_tree_dimensions,
)
from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.model_creator import init_ifc_project, validate_ifc
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models import TreeRecord

logger = get_level_logger("trees_basic_app")

DEFAULT_OUTPUT_NAME = "output_trees_basic.ifc"
DEFAULT_LEVEL_OF_GEOMETRY: int = 1

# Colour strings passed to ``IfcSnippets.assign_color_to_element``
# (``"R, G, B"`` with 0-255 components). Kept as strings to preserve
# the existing geometry unchanged.
_TRUNK_COLOR: str = "111, 70, 46"
_CROWN_COLOR: str = "33, 128, 45"

# Minimum crown radius (m) so small-crown trees stay visible at LOD 1.
_MIN_CROWN_RADIUS_M: float = 1.0

# Trunk polygon segments. Keep at 5 to match the existing output.
_TRUNK_SEGMENTS: int = 5


class TreesBasicApp:
    """Record-builder app: ``list[TreeRecord] -> IFC path`` (mesh geometry)."""

    @staticmethod
    def build_ifc(
        records: List[TreeRecord],
        *,
        output_path: Optional[Union[str, Path]] = None,
        include_property_sets: bool = True,
        project_name: str = "Trees_Basic_Project",
        site_name: str = "Trees_Basic_Site",
        building_name: Optional[str] = None,
        level_of_geom: int = DEFAULT_LEVEL_OF_GEOMETRY,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = 1.0,
        basepoint_psets: Optional[Dict[str, Any]] = None,
        validate: bool = False,
        phase_timings: Optional[Dict[str, float]] = None,
    ) -> Optional[Path]:
        """Build an IFC model from a list of :class:`TreeRecord`.

        Args:
            records: Pre-prepared tree records. Use
                :func:`BIMFabrikHH_core.apps.trees.processing.dataframe_to_records`
                to produce this list from a DataFrame.
            output_path: Target IFC path. If ``None`` the file is written
                to the package output directory using
                ``DEFAULT_OUTPUT_NAME``.
            include_property_sets: If ``True`` (default) every pset stored
                on each record is attached via ``ifcopenshell.api.pset``.
            project_name / site_name / building_name: Used when the IFC
                project skeleton is built.
            level_of_geom: Icosphere level of detail for the crown.
            basepoint_origin: Optional ``(x, y)`` origin in the project
                CRS (currently EPSG:25832). When given, a basepoint quad
                is placed at that origin.
            basepoint_size: Size of the basepoint quad, in metres.
            basepoint_psets: Optional dict of property-set groups attached
                to the basepoint.
            validate: When ``True``, run ``ifcopenshell.validate --rules``
                on the written file.
            phase_timings: Mutable dict receiving per-phase wall time
                (seconds) under the keys ``project_setup_s``,
                ``tree_geometry_s``, ``tree_pset_s``, ``basepoint_s`` and
                ``save_s``.

        Returns:
            Absolute path of the saved IFC file, or ``None`` when
            ``records`` is empty.
        """
        if not records:
            logger.warning(
                "TreesBasicApp.build_ifc called with 0 records; nothing to do."
            )
            return None

        _t_proj = time.perf_counter()
        builder = init_ifc_project(
            project_name=project_name,
            site_name=site_name,
            building_name=building_name,
        )
        model = builder.model
        if model is None:
            logger.warning("IfcModelBuilder did not produce a model; aborting.")
            return None
        if phase_timings is not None:
            phase_timings["project_setup_s"] = time.perf_counter() - _t_proj

        snippets = IfcSnippets()

        for idx, record in enumerate(records, 1):
            try:
                dims = resolve_tree_dimensions(
                    record, min_crown_radius_m=_MIN_CROWN_RADIUS_M
                )
                pset_models = collect_pydantic_psets(
                    record, include_property_sets=include_property_sets
                )

                _t0 = time.perf_counter()
                product = _write_tree(
                    model,
                    record=record,
                    idx=idx,
                    dims=dims,
                    body=builder.body,
                    container=builder.site,
                    level_of_geom=level_of_geom,
                    snippets=snippets,
                )
                if phase_timings is not None:
                    phase_timings["tree_geometry_s"] = phase_timings.get(
                        "tree_geometry_s", 0.0
                    ) + (time.perf_counter() - _t0)
            except Exception as e:
                logger.error(
                    "Failed to create tree %d (%s): %s", idx, record.name, e
                )
                continue

            if not pset_models:
                continue

            try:
                _t0 = time.perf_counter()
                _attach_psets(model, product, pset_models)
                if phase_timings is not None:
                    phase_timings["tree_pset_s"] = phase_timings.get(
                        "tree_pset_s", 0.0
                    ) + (time.perf_counter() - _t0)
            except Exception as e:
                logger.error(
                    "Error creating psets for tree %s: %s", record.name, e
                )

        if basepoint_origin is not None:
            _t_bp = time.perf_counter()
            place_basepoint(
                model=model,
                site=builder.site,
                basepoint_origin=basepoint_origin,
                size=basepoint_size,
                psets=basepoint_psets or {},
            )
            if phase_timings is not None:
                phase_timings["basepoint_s"] = time.perf_counter() - _t_bp

        _t_save = time.perf_counter()
        try:
            file_path = builder.save_ifc_to_output(
                DEFAULT_OUTPUT_NAME, output_path=output_path
            )
        except IOError as e:
            logger.error("Error saving IFC model: %s", e)
            return None
        if phase_timings is not None:
            phase_timings["save_s"] = time.perf_counter() - _t_save

        if file_path is None:
            return None

        result = Path(str(file_path))
        logger.info("IFC model saved to %s", result)

        if validate:
            validate_ifc(result)

        return result


# ---------------------------------------------------------------------------
# Per-tree IFC writers (side-effectful — they mutate ``model``).
# ---------------------------------------------------------------------------


def _write_tree(
    model: Any,
    *,
    record: TreeRecord,
    idx: int,
    dims: TreeDimensions,
    body: Any,
    container: Any,
    level_of_geom: int,
    snippets: IfcSnippets,
) -> Any:
    """Write trunk + crown + aggregate for one tree and return the aggregate."""
    name = record.name or f"Baum_{idx:04d}"
    tree = root.create_entity(
        model, ifc_class="IfcBuildingElementProxy", name=name
    )
    trunk = root.create_entity(
        model, ifc_class="IfcBuildingElementProxy", name=f"Stamm_{idx:04d}"
    )
    crown = root.create_entity(
        model, ifc_class="IfcBuildingElementProxy", name=f"Krone_{idx:04d}"
    )

    x, y, z = (float(v) for v in record.position)

    _write_trunk(
        model,
        body=body,
        trunk_entity=trunk,
        x=x,
        y=y,
        z=z,
        radius=dims.trunk_radius,
        height=dims.trunk_height,
        snippets=snippets,
    )
    _write_crown(
        model,
        body=body,
        crown_entity=crown,
        x=x,
        y=y,
        z=z + dims.trunk_height,
        radius=dims.crown_radius,
        level_of_geom=level_of_geom,
        snippets=snippets,
    )

    spatial.assign_container(
        model, relating_structure=container, products=[tree]
    )
    aggregate.assign_object(
        model, relating_object=tree, products=[crown, trunk]
    )
    return tree


def _write_trunk(
    model: Any,
    *,
    body: Any,
    trunk_entity: Any,
    x: float,
    y: float,
    z: float,
    radius: float,
    height: float,
    snippets: IfcSnippets,
) -> None:
    vertices, faces = _trunk_mesh(radius=radius, height=height)
    representation = ifc_geometry.add_mesh_representation(
        model, context=body, vertices=[vertices], faces=[faces], edges=None
    )
    ifc_geometry.assign_representation(
        model, product=trunk_entity, representation=representation
    )
    ifc_geometry.edit_object_placement(
        model, matrix=_placement_matrix(x, y, z), product=trunk_entity
    )
    snippets.assign_color_to_element(model, representation, _TRUNK_COLOR, 0.0)


def _write_crown(
    model: Any,
    *,
    body: Any,
    crown_entity: Any,
    x: float,
    y: float,
    z: float,
    radius: float,
    level_of_geom: int,
    snippets: IfcSnippets,
) -> None:
    representation = _crown_representation(model, body, radius, level_of_geom or 1)
    ifc_geometry.assign_representation(
        model, product=crown_entity, representation=representation
    )
    snippets.assign_color_to_element(model, representation, _CROWN_COLOR, 0.0)
    run(
        "geometry.edit_object_placement",
        model,
        matrix=_crown_placement_matrix(x, y, z),
        product=crown_entity,
    )


def _attach_psets(model: Any, product: Any, pset_models: List[BaseModel]) -> None:
    """Attach every Pydantic pset model to ``product`` via ``ifcopenshell.api.pset``."""
    for model_obj in pset_models:
        pset_name = getattr(type(model_obj), "pset_name", None) or type(
            model_obj
        ).__name__
        properties = _pydantic_pset_to_ifc_dict(model_obj)
        if not properties:
            continue
        pset_ifc = pset.add_pset(model, product=product, name=pset_name)
        pset.edit_pset(model, pset=pset_ifc, properties=properties)


# ---------------------------------------------------------------------------
# Pure mesh / matrix / conversion helpers (no IFC side effects).
# ---------------------------------------------------------------------------


def _trunk_mesh(
    radius: float, height: float, segments: int = _TRUNK_SEGMENTS
) -> Tuple[list, list]:
    """Build a simple cylindrical polygon trunk mesh, closed bottom."""
    angle_step = 2 * np.pi / segments
    bottom = [
        (
            float(radius * np.cos(i * angle_step)),
            float(radius * np.sin(i * angle_step)),
            0.0,
        )
        for i in range(segments)
    ]
    top = [(vx, vy, float(height)) for (vx, vy, _) in bottom]
    vertices = bottom + top

    faces: list = []
    for i in range(segments):
        next_i = (i + 1) % segments
        faces.append((i, next_i, i + segments))
        faces.append((next_i, next_i + segments, i + segments))
    faces.append(tuple(range(segments - 1, -1, -1)))
    return vertices, faces


def _crown_representation(
    model: Any, body: Any, radius: float, level_of_detail: int
) -> Any:
    vertices, faces = icosphere(level_of_detail)
    vertices = _scale_sphere_vertices(vertices, radius)

    vertices_list = [tuple(float(item) for item in row) for row in vertices]
    faces_list = [tuple(int(item) for item in row) for row in faces]

    return ifc_geometry.add_mesh_representation(
        model,
        context=body,
        vertices=[vertices_list],
        faces=[[list(face) for face in faces_list]],
        edges=None,
    )


def _scale_sphere_vertices(vertices: np.ndarray, radius: float) -> np.ndarray:
    """Scale unit-sphere vertices to the desired crown radius."""
    norms = np.linalg.norm(vertices, axis=1, keepdims=True)
    return (vertices / norms) * radius


def _placement_matrix(x: float, y: float, z: float) -> np.ndarray:
    matrix = np.eye(4)
    matrix[:, 3][0:3] = (x, y, z)
    return matrix


def _crown_placement_matrix(x: float, y: float, z: float) -> np.ndarray:
    matrix = np.eye(4)
    matrix = placement.rotation(random.randint(5, 85), "Z") @ matrix
    matrix = placement.rotation(random.randint(5, 140), "X") @ matrix
    matrix[:, 3][0:3] = (x, y, z)
    return matrix


def _pydantic_pset_to_ifc_dict(model_obj: BaseModel) -> Dict[str, Any]:
    """Convert a Pydantic pset model to a flat dict usable by ``edit_pset``.

    * Uses ``by_alias=True`` so serialization aliases (e.g. ``_Baumnummer``)
      are used as IFC property names.
    * Drops ``None`` values so they don't shadow defaults.
    * Unwraps ``pint.Quantity`` values to their numeric magnitude (float)
      to match plain-numeric IFC real properties.
    """
    raw = model_obj.model_dump(by_alias=True, exclude_none=True)
    out: Dict[str, Any] = {}
    for key, value in raw.items():
        if hasattr(value, "to_base_units") and hasattr(value, "magnitude"):
            out[key] = float(value.to_base_units().magnitude)
        else:
            out[key] = value
    return out
