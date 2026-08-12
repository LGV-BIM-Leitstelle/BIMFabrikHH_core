"""
Basic Terrain Application

Copyright (C) 2025 Freie und Hansestadt Hamburg, Landesbetrieb Geoinformation und Vermessung
BIM-Leitstelle, Ahmed Salem <ahmed.salem@gv.hamburg.de>

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

Record-builder terrain app: takes a :class:`TerrainMesh` and writes an
IFC file. Pure meshing lives in ``apps.terrain.processing``; this file
only does the IFC writing and the convenience ``from_geotiffs`` one-shot
that combines both steps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple, Union

import numpy as np
from ifcopenshell.api import geometry, pset, root, spatial
from pydantic import BaseModel

from BIMFabrikHH_core.apps.terrain._ifc_common import default_terrain_psets
from BIMFabrikHH_core.apps.terrain.processing import extract_mesh_adaptive
from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.georeferencing import bbox_request_params_to_epsg25832
from BIMFabrikHH_core.core.model_creator import init_ifc_project
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import (
    extract_psets_basepoint,
)
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_psets_terrain import (
    Pset_Objektinformation_DGM,
)
from BIMFabrikHH_core.data_models.terrain_mesh import TerrainMesh

logger = get_logger("terrain_basic_app")

_TERRAIN_COLOR: str = "102, 204, 0"
_DEFAULT_BASEPOINT_SIZE: float = 5.0
_DEFAULT_OUTPUT_NAME: str = "output_dgm.ifc"


# ---------------------------------------------------------------------------
# Public app class
# ---------------------------------------------------------------------------


class TerrainBasicApp:
    """Record-builder terrain app.

    Writes an IFC DGM from a :class:`TerrainMesh`. The mesh is generated
    upstream by :func:`BIMFabrikHH_core.apps.terrain.processing.extract_mesh_adaptive`
    (or any other caller-supplied producer). The convenience class method
    :meth:`from_geotiffs` runs the default extractor and then builds the IFC
    in one call.
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
        color: str = _TERRAIN_COLOR,
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
            color: RGB string used for the terrain surface style.

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

            element = _create_terrain_element(model, builder.site, mesh, builder.body, color=color)
            if element is None:
                return None

            effective_psets = list(psets) if psets is not None else default_terrain_psets()
            _attach_psets(model, element, effective_psets)

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
        )


# ---------------------------------------------------------------------------
# Module-level IFC writer helpers
# ---------------------------------------------------------------------------


def _create_terrain_element(
    model,
    site,
    mesh: TerrainMesh,
    body_context,
    *,
    color: str,
):
    """Create the ``IfcBuildingElementProxy`` carrying the terrain mesh."""
    element = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name="DGM")
    if element is None:
        logger.error("Failed to create terrain element")
        return None

    if site is not None:
        spatial.assign_container(model, relating_structure=site, products=[element])
    geometry.edit_object_placement(model, matrix=np.eye(4), product=element)

    representation = geometry.add_mesh_representation(
        model,
        context=body_context,
        vertices=[mesh.vertices],
        faces=[mesh.faces],
        edges=[[]],
    )
    if representation is None:
        logger.error("Failed to create mesh representation")
        return None

    geometry.assign_representation(model, product=element, representation=representation)
    IfcSnippets().assign_color_to_element(model, representation, color, 0.0)
    return element


def _attach_psets(model, product, pset_models: Sequence[BaseModel]) -> None:
    """Attach every Pydantic pset model to ``product`` via ``ifcopenshell.api.pset``."""
    for model_obj in pset_models:
        pset_name = getattr(type(model_obj), "pset_name", None) or type(model_obj).__name__
        properties = _pydantic_pset_to_ifc_dict(model_obj)
        if not properties:
            continue
        pset_ifc = pset.add_pset(model, product=product, name=pset_name)
        pset.edit_pset(model, pset=pset_ifc, properties=properties)


def _pydantic_pset_to_ifc_dict(model_obj: BaseModel) -> Dict[str, Any]:
    """Convert a Pydantic pset model to a flat dict usable by ``edit_pset``.

    * Uses ``by_alias=True`` so serialization aliases (e.g. ``_ArtDGM``)
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


__all__ = ["TerrainBasicApp", "Pset_Objektinformation_DGM"]
