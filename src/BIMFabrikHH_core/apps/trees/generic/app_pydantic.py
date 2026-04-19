"""
Tree Application using Pydantic Approach
=======================================

This module provides an application class for building tree models using
the pydantic-based approach with configurable property sets.
"""

import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from ifcfactory import BIMFactoryElement
from pydantic import BaseModel

from BIMFabrikHH_core.core.geometry.tree_objects_generic import create_tree_element
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates


class BaumPydanticApp:
    """Application class for building tree models using pydantic approach."""

    @staticmethod
    def build_ifc_from_tree_data(
        tree_data: List[Dict],
        output_path: Optional[Union[str, Path]] = None,
        include_property_sets: bool = True,
        trunk_color: tuple = (112, 69, 46),
        crown_color: tuple = (33, 128, 46),
        trunk_layer: str = "_BIM_SBK_Stamm",
        crown_layer: str = "_BIM_SBK_Krone",
        name_prefix: str = "",
        on_progress: Optional[Callable[[], None]] = None,
        phase_timings: Optional[Dict[str, float]] = None,
    ) -> Path:
        """
        Build an IFC model from a list of tree data dicts using pydantic approach.

        Args:
            tree_data: List of tree data dicts (each with position, etc.)
            output_path: Path to save the IFC file.
                If None, saves to output_baum_pydantic.ifc in current dir.
            include_property_sets: Whether to include property sets in the model
            trunk_color: RGB as ``(R, G, B)`` with 0-255 **or** normalized 0-1 floats; ifcfactory
                ``Style`` accepts both (default trunk brown ``(112, 69, 46)``).
            crown_color: Same as ``trunk_color`` (default crown green ``(33, 128, 46)``).
            trunk_layer: CAD layer name for trunk geometry (default: "_BIM_SBK_Stamm")
            crown_layer: CAD layer name for crown geometry (default: "_BIM_SBK_Krone")
            name_prefix: Prefix to add to tree names (e.g., "SBK_Mengestrasse_")
            on_progress: Optional callback called after each tree is built, for progress tracking.
            phase_timings: If given, cumulative seconds are written for ``project_setup_s``,
                ``prepare_elements_s`` (``create_tree_element`` loop), ``build_in_s``,
                ``save_s``.

        Returns:
            Path to the saved IFC file.
        """
        # Create model and contexts
        _t0 = time.perf_counter()
        model_builder = IfcModelBuilder()
        model_builder.build_project(
            project_name="Tree_Pydantic_Project",
            coordinate_system=CoordinateSystemTemplates.gauss_kruger_hamburg(),
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name="Tree_Pydantic_Site",
        )
        if phase_timings is not None:
            phase_timings["project_setup_s"] = time.perf_counter() - _t0

        model = model_builder.model
        site = model_builder.site
        body_context = model_builder.model3d

        # Collect valid tree elements first, then build them all in one batched
        # call via BIMFactoryElement.build_in() — O(n) instead of O(n²).
        tree_elements = []

        _t0 = time.perf_counter()
        for idx, tree_dict in enumerate(tree_data, 1):
            try:
                # Extract tree attributes
                kronendurchmesser = float(tree_dict.get("kronendurchmesser", 5.0))
                stammdurchmesser = float(tree_dict.get("stammdurchmesser", 0.6))
                detail = int(tree_dict.get("detail", 1))
                segments = int(tree_dict.get("segments", 8))
                position = tree_dict.get("position", (0, 0, 0))
                tree_name = tree_dict.get("name", f"Baum_{idx:03d}")

                # Get property sets from tree_dict if provided
                psets = tree_dict.get("psets", None) if include_property_sets else None
                pset_templates = []
                if psets:
                    for pset_name, pset_data in psets.items():
                        if isinstance(pset_data, BaseModel):
                            pset_templates.append(pset_data)
                        else:
                            logging.warning(
                                f"Tree {tree_name}: Property set '{pset_name}' is not a BaseModel instance (type: {type(pset_data)}). Skipping."
                            )
                elif include_property_sets:
                    logging.warning(f"Tree {tree_name}: No property sets found in tree_dict (psets={psets})")

                # Calculate derived values
                crown_radius = kronendurchmesser / 2
                # Clamp to a visible minimum (5 cm diameter) so a 0.0 or near-zero
                # stammdurchmesser (e.g. newly planted tree) never produces a degenerate cylinder.
                MIN_TRUNK_RADIUS = 0.025  # 5 cm diameter
                trunk_radius = max(MIN_TRUNK_RADIUS, stammdurchmesser / 2)
                crown_diameter = kronendurchmesser

                # Calculate tree height using consistent logic
                extracted_height = tree_dict.get("baumhoehe")
                if extracted_height and extracted_height > 0:
                    tree_height = float(extracted_height)
                    trunk_height = tree_height + crown_radius
                elif crown_diameter < 3:
                    tree_height = 3.5
                    trunk_height = 3.5
                else:
                    trunk_height = 1.35 * crown_diameter
                    tree_height = trunk_height - crown_radius

                tree_elements.append(
                    create_tree_element(
                        position=position,
                        crown_radius=crown_radius,
                        trunk_radius=trunk_radius,
                        trunk_height=trunk_height,
                        crown_detail=detail,
                        trunk_segments=segments,
                        psets=pset_templates,
                        trunk_color=trunk_color,
                        crown_color=crown_color,
                        name=tree_name,
                        name_prefix=name_prefix,
                        trunk_layer=trunk_layer,
                        crown_layer=crown_layer,
                    )
                )

            except Exception as e:
                logging.error(f"Failed to create tree {idx}: {e}")
                continue

        if phase_timings is not None:
            phase_timings["prepare_elements_s"] = time.perf_counter() - _t0

        # Build all trees and assign them to the site in one batched call.
        _t0 = time.perf_counter()
        BIMFactoryElement.build_in(model, inst=site, items=tree_elements, on_progress=on_progress)
        if phase_timings is not None:
            phase_timings["build_in_s"] = time.perf_counter() - _t0

        # Save to file
        _t0 = time.perf_counter()
        if output_path is None:
            file_path = model_builder.save_ifc_to_output("output_baum_pydantic.ifc")
        else:
            op = Path(output_path)
            file_path = model_builder.save_ifc_to_output(op.name, output_path=op)
        if phase_timings is not None:
            phase_timings["save_s"] = time.perf_counter() - _t0

        logging.info(f"IFC model saved to {file_path}")
        return Path(str(file_path))
