from typing import List, Optional, Tuple, Union

import ifcopenshell.util.placement
import numpy as np
from ifcopenshell.api import material, pset, style
from ifcopenshell.entity_instance import entity_instance
from ifcopenshell.util.element import get_psets


class IfcSnippets:
    @staticmethod
    def convert_hex_to_rgb(hex_color):
        """Normalize hex color to RGB values in the range [0.1, 1].

        Args:
            hex_color (str): Hexadecimal color string.

        Returns:
            List[float]: Normalized RGB values.
        """

        # Removing the hash symbol
        hex_color = hex_color.lstrip("#")

        # Converting hex to RGB values
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # print(f"RGB values: ({r}, {g}, {b})")
        return [r, g, b]

    @staticmethod
    def ifc_normalise_color(rgb_color_str) -> List[float]:
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
        cls, model: ifcopenshell.file, representation: entity_instance, color_rgb: Union[str, Tuple[float]], transparency: Optional[float]
    ) -> None:
        """Assign a color to the IFC element representation or item"""
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
                **({"Transparency": transparency} if transparency is not None else {})
            },
        )
        if representation.is_a('IfcRepresentation'):
            style.assign_representation_styles(model, shape_representation=representation, styles=[style_ifc])
        elif representation.is_a('IfcRepresentationItem'):
            style.assign_item_style(model, item=representation, style=style_ifc)
        else:
            raise TypeError(f"Unable to assign style to instance of type {representation.is_a()}")

    @staticmethod
    def create_material(model, name, category):
        return material.add_material(model, name=name, category=category)

    @staticmethod
    def parse_coordinates(coord_str):
        """Convert a coordinate string 'x,y' to a NumPy array of floats."""
        x_str, y_str = coord_str.split(",")
        return np.array([float(x_str), float(y_str)])

    @staticmethod
    def get_angle_from_2pts(p1, p2):
        # Splitting input points and converting to float
        try:
            x1, y1 = map(float, p1.split(","))
            x2, y2 = map(float, p2.split(","))
        except (AttributeError, ValueError) as e:
            print(f"Error processing points: {e}")
            return 0  # or set a default_data return value

        # Defining the origin and the point representing the rotation
        origin = np.array([x1, y1, 0], dtype=float)
        rotation_point = np.array([x2, y2, 0], dtype=float)

        # Computing the vector from the origin to the rotation point
        rotation_vector = rotation_point - origin

        # Checking for zero vector to avoid division by zero
        if np.linalg.norm(rotation_vector) == 0:
            print("The two points are the same, angle is undefined.")
            return None  # or set a default_data return value

        # Computing the angle between the X-axis and the rotation vector
        x_axis = np.array([1, 0, 0], dtype=float)
        cos_angle = np.dot(x_axis, rotation_vector) / (np.linalg.norm(x_axis) * np.linalg.norm(rotation_vector))

        # Clamping cos_angle to avoid invalid input for arccos
        cos_angle = np.clip(cos_angle, -1.0, 1.0)

        angle = np.arccos(cos_angle)

        # Converting the angle from radians to degrees
        angle_degrees = np.degrees(angle)

        # Adjusting the angle based on the Y-component to account for points above/below the origin
        if rotation_vector[1] < 0:
            angle_degrees = 360 - angle_degrees

        return angle_degrees

    @staticmethod
    def add_psets(model, element, pset_name):
        pset_ifc = pset.add_pset(model, product=element, name=pset_name)
        # run("pset.edit_pset", model, pset=pset_ifc, properties={"foo": "foobar", "foo2": "foobaz"})
        return pset_ifc

    @staticmethod
    def edit_pset_data(model, elements, pset_classes, pset_names):
        for element in elements:
            psets_obj = get_psets(element)

            for pset_class, pset_name in zip(pset_classes, pset_names):

                pset_id = model.by_id(psets_obj[pset_name]["id"])

                pset.edit_pset(model, pset=pset_id, properties=pset_class.dict(by_alias=True))
