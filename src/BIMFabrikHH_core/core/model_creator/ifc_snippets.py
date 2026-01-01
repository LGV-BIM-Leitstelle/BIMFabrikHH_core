from typing import List, Optional, Tuple, Union

import ifcopenshell
import ifcopenshell.util.placement
from ifcopenshell.api import material, style
from ifcopenshell.entity_instance import entity_instance

from BIMFabrikHH_core.config.logging_colors import get_level_logger

# Configure logger for this module
logger = get_level_logger("ifc_snippets")


class IfcSnippets:
    """
    Utility class for common IFC operations and snippets.

    This class provides static methods for color processing, material creation,
    coordinate parsing, and angle calculations used in IFC model creation.
    """

    def __init__(self) -> None:
        """Initialize IfcSnippets class."""

    @staticmethod
    def convert_hex_to_rgb(hex_color: str) -> List[float]:
        """
        Normalize hex color to RGB values in the range [0.1, 1].

        Args:
            hex_color (str): Hexadecimal color string (e.g., "#FF0000").

        Returns:
            List[float]: Normalized RGB values as a list of three floats.

        Raises:
            ValueError: If hex_color is not a valid hexadecimal color string.
        """
        # Removing the hash symbol
        hex_color = hex_color.lstrip("#")

        # Converting hex to RGB values
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # logger.debug(f"RGB values: ({r}, {g}, {b})")
        return [r, g, b]

    @staticmethod
    def ifc_normalise_color(rgb_color_str: str) -> List[float]:
        """
        Normalize RGB color string to IFC-compatible values in range [0.1, 1].

        Args:
            rgb_color_str (str): RGB color string in format "r,g,b" (e.g., "255,0,0").

        Returns:
            List[float]: Normalized RGB values as a list of three floats.

        Raises:
            ValueError: If rgb_color_str is not in the expected format.
        """
        rgb_color = rgb_color_str.split(",")
        r, g, b = (float(rgb_color[0]), float(rgb_color[1]), float(rgb_color[2]))

        # Normalizing RGB values to the range [0.1, 1]
        normalized_rgb = [
            round(r / 255 * (1 - 0.1) + 0.1, 2),
            round(g / 255 * (1 - 0.1) + 0.1, 2),
            round(b / 255 * (1 - 0.1) + 0.1, 2),
        ]

        return normalized_rgb

    @classmethod
    def assign_color_to_element(
        cls,
        model: ifcopenshell.file,
        representation: entity_instance,
        color_rgb: Union[str, Tuple[float, ...]],
        transparency: Optional[float],
    ) -> None:
        """
        Assign a color to the IFC element representation or item.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            representation (entity_instance): The IFC representation or representation item.
            color_rgb (Union[str, Tuple[float, ...]]): Color as RGB string or tuple.
            transparency (Optional[float]): Transparency value (0.0 to 1.0).

        Raises:
            TypeError: If representation is not a valid IFC representation type.
        """
        value = IfcSnippets.ifc_normalise_color(color_rgb) if isinstance(color_rgb, str) else color_rgb

        # Creating a new style
        style_ifc = style.add_style(model, name="Style")

        style.add_surface_style(
            model,
            style=style_ifc,
            ifc_class="IfcSurfaceStyleShading",
            attributes={
                "SurfaceColour": {
                    "Name": None,
                    "Red": value[0],
                    "Green": value[1],
                    "Blue": value[2],
                },
                **({"Transparency": transparency} if transparency is not None else {}),
            },
        )
        if representation.is_a("IfcRepresentation"):
            style.assign_representation_styles(model, shape_representation=representation, styles=[style_ifc])
        elif representation.is_a("IfcRepresentationItem"):
            style.assign_item_style(model, item=representation, style=style_ifc)
        else:
            raise TypeError(f"Unable to assign style to instance of type {representation.is_a()}")

    @staticmethod
    def create_material(model: ifcopenshell.file, name: str, category: str) -> entity_instance:
        """
        Create a material in the IFC model.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            name (str): Name of the material.
            category (str): Category of the material.

        Returns:
            entity_instance: The created material entity.
        """
        return material.add_material(model, name=name, category=category)

    @staticmethod
    def assign_color_to_representation(
        model, representation: ifcopenshell.entity_instance, color_rgb: tuple, transparency: float
    ) -> None:
        """Assign color to representation using the improved method that works better with BricsCAD.

        This method follows the pattern from the working color_set_change.py example.

        Args:
            representation: The representation to assign color to.
            color_rgb: Normalized RGB tuple (floats in [0,1]).
            transparency: Transparency value (0.0 = opaque, 1.0 = transparent).
        """
        try:

            if not (
                isinstance(color_rgb, tuple)
                and len(color_rgb) == 3
                and all(isinstance(c, (float, int)) and 0.0 <= c <= 1.0 for c in color_rgb)
            ):
                print(f"Warning: color_rgb must be a tuple of three floats in [0,1], got {color_rgb}")
                return
            normalized_rgb = list(color_rgb)

            # Create color entity
            color_entity = model.create_entity(
                "IfcColourRgb",
                Name=f"Color_{normalized_rgb}",
                Red=normalized_rgb[0],
                Green=normalized_rgb[1],
                Blue=normalized_rgb[2],
            )

            # Create surface style rendering
            surface_rendering = model.create_entity(
                "IfcSurfaceStyleRendering", SurfaceColour=color_entity, Transparency=transparency
            )

            # Create surface style
            surface_style = model.create_entity(
                "IfcSurfaceStyle", Name=f"Style_{normalized_rgb}", Side="BOTH", Styles=[surface_rendering]
            )

            # Create presentation style assignment
            style_assignment = model.create_entity("IfcPresentationStyleAssignment", Styles=[surface_style])

            # Apply style to each item in the representation
            if hasattr(representation, "Items") and representation.Items:
                for item in representation.Items:
                    styled_item = model.create_entity("IfcStyledItem", Item=item, Styles=[style_assignment])

        except Exception as e:
            print(f"Warning: Could not assign color '{color_rgb}' to representation: {e}")

    @staticmethod
    def assign_layer_to_representation(
        model,
        representation: ifcopenshell.entity_instance,
        layer_name: str,
        color: tuple = (1.0, 1.0, 1.0),
        transparency: float = 0.0,
    ) -> None:
        """
        Assign a layer to the given representation, reusing or creating IfcPresentationLayerWithStyle.
        Args:
            model: The IFC model instance.
            representation: The representation to assign to the layer.
            layer_name: Name of the layer.
            color: Normalized RGB tuple for the layer style (default: white).
            transparency: Transparency for the layer style (default: 0.0).
        """
        try:

            items_to_assign = []

            # Assign the representation itself if it's a geometric solid
            if hasattr(representation, "is_a") and representation.is_a() in [
                "IfcExtrudedAreaSolid",
                "IfcTriangulatedFaceSet",
                "IfcPolygonalFaceSet",
                "IfcMappedItem",
                "IfcSweptDiskSolid",
            ]:
                items_to_assign.append(representation)

            # Add geometry items from the representation if present
            if hasattr(representation, "Items") and representation.Items:
                for item in representation.Items:

                    items_to_assign.append(item)
                    if hasattr(item, "is_a") and item.is_a("IfcMappedItem"):
                        items_to_assign.append(item)

            # Add the representation itself if it's a mapped representation
            if hasattr(representation, "is_a") and representation.is_a("IfcShapeRepresentation"):
                if getattr(representation, "RepresentationType", "") == "MappedRepresentation":
                    items_to_assign.append(representation)

            # Remove duplicates
            items_to_assign = list(dict.fromkeys(items_to_assign))

            # Don't create layer if no items to assign (prevents BricsCAD errors)
            if not items_to_assign:
                return

            # Create surface style for the layer
            layer_color = model.create_entity(
                "IfcColourRgb", Name="LayerColor", Red=color[0], Green=color[1], Blue=color[2]
            )
            surface_style_shading = model.create_entity(
                "IfcSurfaceStyleShading", SurfaceColour=layer_color, Transparency=transparency
            )
            surface_style = model.create_entity(
                "IfcSurfaceStyle", Name="LayerStyle", Side="POSITIVE", Styles=[surface_style_shading]
            )

            # Check if layer already exists
            existing_layer = None
            for layer in model.by_type("IfcPresentationLayerWithStyle"):
                if layer.Name == layer_name:
                    existing_layer = layer
                    break

            if existing_layer:
                existing_items = list(existing_layer.AssignedItems) if existing_layer.AssignedItems else []
                existing_items.extend(items_to_assign)
                existing_layer.AssignedItems = list(dict.fromkeys(existing_items))
            else:
                model.create_entity(
                    "IfcPresentationLayerWithStyle",
                    Name=layer_name,
                    Description=None,
                    AssignedItems=items_to_assign,
                    LayerOn=True,
                    LayerFrozen=False,
                    LayerBlocked=False,
                    LayerStyles=[surface_style],
                )

            # Also assign mapped items to the layer
            if hasattr(representation, "Items") and representation.Items:
                for item in representation.Items:
                    if hasattr(item, "is_a") and item.is_a("IfcMappedItem"):
                        if existing_layer:
                            existing_items = list(existing_layer.AssignedItems) if existing_layer.AssignedItems else []
                            if item not in existing_items:
                                existing_items.append(item)
                                existing_layer.AssignedItems = existing_items
                        else:
                            model.create_entity(
                                "IfcPresentationLayerWithStyle",
                                Name=layer_name,
                                Description=None,
                                AssignedItems=[item],
                                LayerOn=True,
                                LayerFrozen=False,
                                LayerBlocked=False,
                                LayerStyles=[surface_style],
                            )

        except Exception as e:
            print(f"Warning: Could not assign layer '{layer_name}': {e}")
