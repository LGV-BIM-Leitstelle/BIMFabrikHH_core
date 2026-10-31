"""
Generic Basepoint App
=====================

IFC with only the **Nullpunktobjekt**: project, site and building with the same
georeferencing, placement and psets as the Nullpunkt of every other generic app.

Built from the same :class:`RequestParams` as the Teilmodelle, so a model of the
same umring, ``output_epsg`` and ``basepoint`` has its Nullpunkt at the same
position and can be used as Mastermodell to check them against each other.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Union

from BIMFabrikHH_core.config.logging_config import get_logger
from BIMFabrikHH_core.core.geometry import place_basepoint
from BIMFabrikHH_core.core.georeferencing import CoordinateTransformer
from BIMFabrikHH_core.core.model_creator import georeference_options, init_ifc_project
from BIMFabrikHH_core.core.ogc_extractor.ogc_values_extractor import extract_psets_basepoint
from BIMFabrikHH_core.data_models.params_tree import RequestParams
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateOperation

logger = get_logger("basepoint_generic_app")

_DEFAULT_OUTPUT_NAME: str = "output_basepoint_generic.ifc"
_DEFAULT_BASEPOINT_SIZE: float = 5.0


class BasepointGenericApp:
    """IFC with only the Nullpunktobjekt of ``request_params``."""

    @staticmethod
    def build_ifc(
        *,
        request_params: RequestParams,
        output_path: Optional[Union[str, Path]] = None,
        output_name: str = _DEFAULT_OUTPUT_NAME,
        coordinate_operation: Optional[CoordinateOperation] = None,
        basepoint_origin: Optional[Tuple[float, float]] = None,
        basepoint_size: float = _DEFAULT_BASEPOINT_SIZE,
    ) -> Optional[Path]:
        """Write the Nullpunktobjekt of ``request_params`` into an otherwise empty IFC.

        The Nullpunkt is ``request_params.basepoint`` (output CRS), else
        ``basepoint_origin`` (source CRS), else the lower-left of the bbox, as in
        :func:`place_basepoint`. Psets come from ``request_params.containers``.

        Returns:
            Path of the written IFC, or ``None`` when no Nullpunkt can be placed
            (no ``basepoint`` and no ``source_epsg`` for the bbox) or writing fails.
        """
        transformer = CoordinateTransformer.from_source_to_output(
            request_params.source_epsg, request_params.output_epsg, request_params.vertical_epsg
        )
        if request_params.basepoint_xyz is None and basepoint_origin is None and transformer is None:
            logger.error("No Nullpunkt: neither basepoint nor a source CRS for the bbox.")
            return None

        try:
            model_builder = init_ifc_project(
                request_params=request_params,
                coordinate_operation=coordinate_operation,
                **georeference_options(transformer),
            )
            if model_builder.model is None:
                logger.error("Failed to create IFC model")
                return None

            place_basepoint(
                model=model_builder.model,
                site=model_builder.site,
                basepoint=request_params.basepoint_xyz,
                basepoint_origin=basepoint_origin,
                bbox_wgs84=request_params.bbox_as_wgs84_tuple if transformer is not None else None,
                size=basepoint_size,
                psets=extract_psets_basepoint(request_params.containers or []),
                transformer=transformer,
            )

            saved_path = model_builder.save_ifc_to_output(output_name, output_path=output_path)
            if not saved_path:
                raise RuntimeError("Failed to save IFC file")
            return Path(str(saved_path))

        except Exception as exc:
            logger.exception("Error creating IFC model: %s", exc)
            return None


__all__ = ["BasepointGenericApp"]
