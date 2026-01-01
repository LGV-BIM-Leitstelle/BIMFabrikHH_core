"""
Tree Application using Pydantic Approach
=======================================

This module provides an application class for building tree models using
the pydantic-based approach with configurable property sets.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

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
        trunk_color: tuple = (0.44, 0.27, 0.18),
        crown_color: tuple = (0.13, 0.50, 0.18),
        trunk_layer: str = "_BIM_SBK_Stamm",
        crown_layer: str = "_BIM_SBK_Krone",
        name_prefix: str = "",
    ) -> Path:
        """
        Build an IFC model from a list of tree data dicts using pydantic approach.

        Args:
            tree_data: List of tree data dicts (each with position, etc.)
            output_path: Path to save the IFC file.
                If None, saves to output_baum_pydantic.ifc in current dir.
            include_property_sets: Whether to include property sets in the model
            trunk_color: RGB tuple for trunk color (default: brown (0.44, 0.27, 0.18))
            crown_color: RGB tuple for crown color (default: green (0.13, 0.50, 0.18))
            trunk_layer: CAD layer name for trunk geometry (default: "_BIM_SBK_Stamm")
            crown_layer: CAD layer name for crown geometry (default: "_BIM_SBK_Krone")
            name_prefix: Prefix to add to tree names (e.g., "SBK_Mengestrasse_")

        Returns:
            Path to the saved IFC file.
        """
        # Create model and contexts
        model_builder = IfcModelBuilder()
        model_builder.build_project(
            project_name="Tree_Pydantic_Project",
            coordinate_system=CoordinateSystemTemplates.gauss_kruger_hamburg(),
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name="Tree_Pydantic_Site",
        )

        model = model_builder.model
        site = model_builder.site
        body_context = model_builder.model3d

        tree_elements = []

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

                # Calculate derived values
                crown_radius = kronendurchmesser / 2
                trunk_radius = stammdurchmesser / 2  # Convert diameter to radius
                crown_diameter = kronendurchmesser

                # Calculate tree height using consistent logic
                extracted_height = tree_dict.get("baumhoehe")
                if extracted_height and extracted_height > 0:
                    # Use provided height
                    tree_height = float(extracted_height)
                    trunk_height = tree_height + crown_radius
                elif crown_diameter < 3:
                    # For small trees: total height is 3.5m, trunk goes to crown center
                    tree_height = 3.5
                    trunk_height = 3.5
                else:
                    # For larger trees: trunk height is 1.35 * crown_diameter, tree height is trunk - crown_radius
                    trunk_height = 1.35 * crown_diameter
                    tree_height = trunk_height - crown_radius

                # Create tree element using tree_objects_generic
                tree_element = create_tree_element(
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

                # Build the tree and assign it to the site
                from ifcfactory import BIMFactoryElement

                BIMFactoryElement(
                    inst=site,
                    children=[tree_element],
                ).build(model)

                tree_elements.append(tree_element)

            except Exception as e:
                logging.error(f"Failed to create tree {idx}: {e}")
                continue

        # Save to file
        if output_path is None:
            file_path = model_builder.save_ifc_to_output("output_baum_pydantic.ifc")
        else:
            file_path = model_builder.save_ifc_to_output(str(Path(output_path).name))

        logging.info(f"IFC model saved to {file_path}")
        return Path(str(file_path))
