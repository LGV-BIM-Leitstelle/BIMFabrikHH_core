"""
IFC Model Builder Module

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
"""

from pathlib import Path
from typing import Optional

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.data_models.pydantic_georeferencing import (
    CoordinateOperation,
    CoordinateSystem,
    CoordinateSystemTemplates,
)

from .ifc_utils import IfcModelMethods


class IfcModelBuilder:
    """
    A class to encapsulate the process of creating an IFC model.
    Provides methods for project creation, property set setup, georeferencing, and saving.
    """

    def __init__(self):
        """
        Initializes IfcModelBuilder with necessary components and property sets.
        """

        self.ifc_snippets = IfcSnippets()
        self.ifc_creator = IfcModelMethods()
        self.model = self.ifc_creator.create_model("IFC4")
        self.logger = get_level_logger("IfcModelBuilder")

        self.all_psets = None
        self.building = None
        self.element_manager = None
        self.project = None
        self.pset_classes = None
        self.site = None
        self.storey = None
        self.model3d = None
        self.plan = None
        self.body = None

    def reset_model(self) -> None:
        """
        Resets the model and initializes necessary components.
        """
        self.model = self.ifc_creator.create_model("IFC4")

        self.all_psets = None
        self.building = None
        self.element_manager = None
        self.project = None
        self.pset_classes = None
        self.site = None
        self.storey = None
        self.model3d = None
        self.plan = None
        self.body = None

    @staticmethod
    def _initialize_psets(*args) -> list:
        """
        Initialize property sets based on provided Pset classes and their data.

        Args:
            *args: Alternating Pset classes and their corresponding data dictionaries.

        Returns:
            list: A list of instantiated property set objects.

        Example:
            _initialize_psets(Pset_Objektinformation, pset_objectinfo_data,
                              Pset_Modellinformation, pset_modellinfo_data)
        """
        return [pset_class(**pset_data) for pset_class, pset_data in zip(args[::2], args[1::2])]

    def build_project(
        self,
        project_name: str,
        coordinate_system: CoordinateSystem | str,
        coordinate_operation: CoordinateOperation,
        site_name: Optional[str] = None,
        building_name: Optional[str] = None,
        storey_name: Optional[str] = None,
    ) -> None:
        """
        Builds the IFC project with the given project information, coordinate system, and coordinate operation.

        Args:
            project_name (str): Name of the project.
            coordinate_system (CoordinateSystem | str): Coordinate system configuration or template name.
            coordinate_operation (CoordinateOperation): Coordinate transformation parameters.
            site_name (Optional[str]): Name of the site.
            building_name (Optional[str]): Name of the building.
            storey_name (Optional[str]): Name of the storey.
        """
        self.project = self.ifc_creator.create_project_entity(self.model, project_name)

        # Add units to the IFC model (e.g., meters)
        self.ifc_creator.create_units_meter(self.model)

        # Create necessary contexts for geometric representation after project is created
        self.model3d, self.plan, self.body = self.ifc_creator.create_contexts(self.model)

        self.site = self.ifc_creator.create_site(self.model, site_name, self.project) if site_name else None
        self.building = (
            self.ifc_creator.create_building(self.model, building_name, self.site) if building_name else None
        )
        self.storey = self.ifc_creator.create_storey(self.model, storey_name, self.building) if storey_name else None

        # Create georeferencing information
        self.ifc_creator.create_georeference(self.model)

        # Handle coordinate system (convert string templates to CoordinateSystem objects)
        if isinstance(coordinate_system, str):
            try:
                coordinate_system = CoordinateSystemTemplates.get_template(coordinate_system)
            except ValueError as e:
                raise ValueError(f"Unknown coordinate system template '{coordinate_system}': {e}")

        # Edit georeferencing with the provided coordinate system and operation
        self.ifc_creator.edit_georeference(self.model, coordinate_system, coordinate_operation)

    def save_ifc_to_memory(self) -> Optional[bytes]:
        """
        Save the current IFC model to memory.

        Returns:
            Optional[bytes]: The IFC file as bytes, or None if saving fails.
        """
        try:
            temp_dir = PathConfig.TEMP
            temp_dir.mkdir(exist_ok=True)
            temp_file = temp_dir / "temp.ifc"
            self.model.write(str(temp_file))

            with open(temp_file, "rb") as f:
                ifc_bytes = f.read()

            temp_file.unlink()
            return ifc_bytes

        except Exception as e:
            self.logger.warning(f"Error saving IFC model to memory: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    def save_ifc_to_output(self, filename: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Save the current IFC model to a file.

        Args:
            filename (str): The filename to save as (used only if output_path is None).
            output_path (Optional[Path]): Full path where to save the file. If provided,
                the parent directory must exist. If None, saves to default OUTPUT directory.

        Returns:
            Optional[Path]: The path to the saved IFC file, or None if saving fails.
        """
        if output_path is None:
            # Default behavior - save to core's output directory
            if not filename:
                self.logger.warning("Filename cannot be empty")
                return None

            output_dir = PathConfig.OUTPUT
            if not output_dir.exists():
                self.logger.warning(f"Output directory does not exist: {output_dir}")
                return None

            safe_filename = Path(filename).name
            file_path = output_dir / safe_filename
        else:
            # Custom path provided - validate that directory exists
            if not output_path.parent.exists():
                raise FileNotFoundError(f"Output directory does not exist: {output_path.parent}")
            file_path = output_path

        try:
            self.logger.info(f"Saving IFC file to {file_path}")
            self.model.write(str(file_path))
            return file_path
        except Exception as e:
            self.logger.warning(f"Failed to save IFC file: {str(e)}")
            return None

    def save_ifc_to_path(self, file_path: Path) -> Optional[Path]:
        """
        Save the current IFC model to a specific path.

        Args:
            file_path (Path): The full path where to save the file.

        Returns:
            Optional[Path]: The path to the saved IFC file, or None if saving fails.
        """
        try:
            self.logger.info(f"Saving IFC file to {file_path}")
            self.model.write(str(file_path))
            return file_path
        except Exception as e:
            self.logger.warning(f"Failed to save IFC file to {file_path}: {str(e)}")
            return None
