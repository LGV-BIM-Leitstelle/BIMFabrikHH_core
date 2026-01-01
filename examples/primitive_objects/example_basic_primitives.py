"""
Basic Primitive Objects Demo
===========================

This example demonstrates the usage of basic primitive geometry objects
for creating simple IFC models with fundamental geometric shapes.
"""

from ifcfactory import BIMFactoryElement, Box, Cube, Cylinder, Extrusion, Rect

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with basic primitive objects."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "basic_primitives_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Create main project structure
    BIMFactoryElement(
        inst=proj,
        children=[
            BIMFactoryElement(
                type="IfcSite",
                children=[
                    BIMFactoryElement(
                        type="IfcBuilding",
                        children=[
                            # Basic box wall
                            BIMFactoryElement(type="IfcWall", children=[Box(width=10.0, depth=0.3, height=3.0)]),
                            # Basic cube wall
                            BIMFactoryElement(type="IfcWall", children=[Cube(size=5.0)]),
                            # Basic cylinder wall
                            BIMFactoryElement(type="IfcWall", children=[Cylinder(radius=2.0, height=4.0)]),
                            # Extrusion from rectangle
                            BIMFactoryElement(
                                type="IfcWall", children=[Extrusion(basis=Rect(width=8.0, height=2.5), depth=0.3)]
                            ),
                        ],
                    )
                ],
            )
        ],
    ).build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Basic primitives model created successfully: {output_file}")


if __name__ == "__main__":
    main()
