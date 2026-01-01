import ifcopenshell
import ifcopenshell.api.geometry as geometry
from ifcfactory import BIMFactoryElement, Boolean, BooleanOperationTypes, Extrusion, Rect, Transform

from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates


def main():
    # Use IfcModelBuilder for IFC creation and setup
    model_builder = IfcModelBuilder()
    coordinate_system = CoordinateSystemTemplates.epsg_25832()
    coordinate_operation = CoordinateSystemTemplates.get_default_coordinate_operation()
    model_builder.build_project(
        "Generic City Model Project",
        coordinate_system,
        coordinate_operation,
        site_name="Site",
        building_name="Building",
    )
    model = model_builder.model
    building = model_builder.building
    storey = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcBuildingStorey", name="Storey")
    # Assign hierarchy
    ifcopenshell.api.run("aggregate.assign_object", model, relating_object=building, products=[storey])

    # Create a custom builder that has the required methods
    class ProperBuilder:
        def __init__(self, ifc_model, body):
            self.model = ifc_model
            self.body = body

        def triangulated_face_set(self, vertices, faces):
            """Create a triangulated face set representation"""
            return geometry.add_mesh_representation(
                self.model, context=self.body, vertices=[vertices], faces=[faces], edges=[[]]
            )

        def get_representation(self, items):
            """Create a representation from items"""
            # For simplicity, return the first item if it's a representation
            if items:
                return items[0]
            return None

        def rectangle(self, size):
            """Create a rectangle representation"""
            width, height = size
            # Create a simple rectangular mesh
            vertices = [[0, 0, 0], [width, 0, 0], [width, height, 0], [0, height, 0]]
            faces = [[0, 1, 2, 3]]
            return self.triangulated_face_set(vertices, faces)

        def extrude(self, basis):
            """Create an extrusion representation"""
            # For simplicity, create a basic extrusion
            # In a real implementation, this would be more complex
            return basis  # Return the basis for now

        def translate(self, item):
            """Transform an item by a vector"""
            # For simplicity, just return the item
            # In a real implementation, this would apply transformation
            return item

    # Create the geometry using the generic concept
    wall_element = BIMFactoryElement(
        type="IfcWall",
        children=[
            Extrusion(
                basis=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        Rect(width=10.0, height=10.0),
                        Transform(translation=(2.0, 2.0), item=Rect(width=6.0, height=6.0)),
                    ],
                ),
                depth=10.0,
            )
        ],
    )
    # Build the wall and assign to storey
    wall_ifc = wall_element.build(model)
    ifcopenshell.api.run("spatial.assign_container", model, products=[wall_ifc], relating_structure=storey)
    # Save the IFC file using the builder's method
    output_path = model_builder.save_ifc_to_output("output_citymodell_generic.ifc")
    print(f"IFC file written to {output_path}")


if __name__ == "__main__":
    main()
