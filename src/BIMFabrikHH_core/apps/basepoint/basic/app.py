from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from BIMFabrikHH_core.core.geometry.advanced_objects import create_basepoint_quad
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystem, CoordinateSystemTemplates


class BasepointBasicApp:
    """
    Application class for building IFC models with basic basepoints.

    This class provides functionality to create IFC models containing basic basepoint entities
    without directional arrows.
    """

    @staticmethod
    def build_ifc_from_basepoint_data(
        basepoint_data: List[Dict[str, Any]],
        output_path: Optional[Union[str, Path]] = None,
        coordinate_system: Optional[Union[CoordinateSystem, str]] = None,
    ) -> str:
        """
        Build IFC model with basic basepoints.

        Args:
            basepoint_data: List of dictionaries containing basepoint information.
                Each dictionary should contain:
                - 'position': Tuple[float, float, float] - 3D coordinates (x, y, z)
                - 'size': float - Size of the basepoint (default: 5.0)
                - 'psets': Dict[str, Any] - Property sets for the basepoint
            output_path: Optional path where to save the IFC file.
                        If None, uses default output directory.
            coordinate_system: Optional coordinate system configuration.
                Can be a CoordinateSystem instance, template name string, or None for default EPSG:25832.

        Returns:
            str: Path to the saved IFC file.

        Raises:
            ValueError: If basepoint_data is empty or invalid.
            IOError: If there's an error saving the IFC file.
        """
        if not basepoint_data:
            raise ValueError("basepoint_data cannot be empty")

        builder = IfcModelBuilder()
        builder.reset_model()
        builder.build_project(
            project_name="MyProject",
            coordinate_system=coordinate_system or "epsg_25832",
            coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
            site_name="MySite",
            building_name="MyBuilding",
        )
        model = builder.model
        # body = builder.body
        # ifc_snippets = IfcSnippets()

        # Create and add basepoints
        from ifcfactory import BIMFactoryElement, Transform

        basepoint_entities = []
        for i, data in enumerate(basepoint_data, 1):
            print(f"Adding basepoint {i}: size={data.get('size', 5.0)}, position={data['position']}")

            # Create basepoint using new approach
            position = data.get("position", (0, 0, 0))
            size = data.get("size", 5.0)
            psets = data.get("psets", {})

            basepoint_factory = create_basepoint_quad(size=size, psets=psets)

            # Create IFC product with translation
            BIMFactoryElement(
                inst=builder.storey or builder.site,
                children=[
                    Transform(
                        vec=position,
                        item=basepoint_factory,
                    ),
                ],
            ).build(model)

            basepoint_entities.append(basepoint_factory)

        print(f"Created {len(basepoint_entities)} basepoints")

        if output_path is None:
            file_path = builder.save_ifc_to_output("output_basepoint_basic.ifc")
        else:
            file_path = builder.save_ifc_to_output(str(Path(output_path).name))
        print(f"IFC model saved to {file_path}")
        return str(file_path)

    @staticmethod
    def build_single_basepoint(
        position: Tuple[float, float, float] = (0, 0, 0),
        size: float = 5.0,
        color: str = "239, 109, 109",
        output_path: Optional[Union[str, Path]] = None,
        coordinate_system: Optional[Union[CoordinateSystem, str]] = None,
    ) -> str:
        """
        Build IFC model with a single basepoint.

        Args:
            position: 3D coordinates (x, y, z) for the basepoint position.
            size: Size of the basepoint in meters.
            color: RGB color string in format "r, g, b".
            output_path: Optional path where to save the IFC file.
                        If None, uses default output directory.
            coordinate_system: Optional coordinate system configuration.
                Can be a CoordinateSystem instance, template name string, or None for default EPSG:25832.

        Returns:
            str: Path to the saved IFC file.

        Raises:
            ValueError: If position is invalid, size is negative, or color format is invalid.
            IOError: If there's an error saving the IFC file.
        """
        if len(position) != 3:
            raise ValueError("position must be a tuple of 3 float values (x, y, z)")

        if size < 0:
            raise ValueError("size must be non-negative")

        # Validate color format
        try:
            color_parts = color.split(",")
            if len(color_parts) != 3:
                raise ValueError("color must be in format 'r, g, b'")
            [float(c.strip()) for c in color_parts]  # Validate all parts are numbers
        except (ValueError, AttributeError):
            raise ValueError("color must be a valid RGB string in format 'r, g, b'")

        basepoint_data = [
            {
                "position": position,
                "size": size,
                "psets": {
                    "BasePoint_Properties": {
                        "Name": "Single Basepoint",
                        "Description": f"Basepoint at position {position}",
                        "Type": "Reference_Point",
                        "Coordinate_System": "UTM32N",
                    }
                },
            }
        ]

        return BasepointBasicApp.build_ifc_from_basepoint_data(basepoint_data, output_path, coordinate_system)
