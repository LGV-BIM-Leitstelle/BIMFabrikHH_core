"""
Project Init
============

Shared one-call constructor for a fresh ``IfcModelBuilder`` with the
project / site / building skeleton set up. Every app (trees, terrain,
city) kicks off with the same boilerplate — extract names from
``RequestParams.containers``, pick a CRS, then call
``builder.build_project(...)``. :func:`init_ifc_project` collapses that
into one call.

Typical use:

>>> builder = init_ifc_project(request_params=rp, building_name="DGM")
>>> model = builder.model
"""

from __future__ import annotations

from typing import Optional

from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_project_info
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
    CoordinateSystemTemplates,
)

from .ifc_modelbuilder import IfcModelBuilder


def init_ifc_project(
    *,
    request_params: Optional[RequestParams] = None,
    project_name: Optional[str] = None,
    site_name: Optional[str] = None,
    building_name: Optional[str] = None,
    coordinate_system: Optional[CoordinateSystem] = None,
    coordinate_operation: Optional[CoordinateOperation] = None,
) -> IfcModelBuilder:
    """Create and initialise an :class:`IfcModelBuilder`.

    Resolution order for the project / site / building names:

    1. Explicit ``project_name`` / ``site_name`` / ``building_name``
       arguments (caller overrides).
    2. When ``request_params`` is given, names are extracted from
       ``request_params.containers`` via :func:`extract_project_info`.
    3. Falls back to the defaults that ``IfcModelBuilder.build_project``
       already applies (``"IfcProjectName"``, ``None``, ``None``).

    ``coordinate_system`` defaults to :meth:`CoordinateSystemTemplates.epsg_25832`
    and ``coordinate_operation`` to
    :meth:`CoordinateSystemTemplates.get_default_coordinate_operation`.

    Args:
        request_params: Optional project parameters carrying containers.
        project_name: Explicit project name override.
        site_name: Explicit site name override.
        building_name: Explicit building name override.
        coordinate_system: Override for the default EPSG:25832 CRS.
        coordinate_operation: Override for the default coordinate operation.

    Returns:
        A ready-to-use :class:`IfcModelBuilder` whose ``model``, ``site``
        and ``building`` attributes are populated.
    """
    extracted_project: Optional[str] = None
    extracted_site: Optional[str] = None
    extracted_building: Optional[str] = None
    if request_params is not None:
        extracted_project, extracted_site, extracted_building = extract_project_info(
            request_params.containers
        )

    crs = coordinate_system or CoordinateSystemTemplates.epsg_25832()
    coord_op = coordinate_operation or CoordinateSystemTemplates.get_default_coordinate_operation()

    builder = IfcModelBuilder()
    builder.build_project(
        project_name=project_name or extracted_project or "IfcProjectName",
        coordinate_system=crs,
        coordinate_operation=coord_op,
        site_name=site_name if site_name is not None else extracted_site,
        building_name=building_name if building_name is not None else extracted_building,
    )
    return builder


__all__ = ["init_ifc_project"]
