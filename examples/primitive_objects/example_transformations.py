"""
Transformations Demo
===================

This example demonstrates the usage of transformations
for moving and rotating primitive objects in 3D space.
"""

from ifcfactory import BIMFactoryElement, Box, Cube, Cylinder, Transform

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with transformations."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "transformations_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Create main project structure (site and building entities)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Example 1: Simple translation
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(0.0, 0.0, 0.0),
                item=BIMFactoryElement(type="IfcWall", children=[Cube(size=5.0)]),
            )
        ],
    ).build(model)

    # Example 2: Translation with offset
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(10.0, 0.0, 0.0),
                item=BIMFactoryElement(type="IfcWall", children=[Box(width=4.0, depth=0.3, height=3.0)]),
            )
        ],
    ).build(model)

    # Example 3: Rotation around Z-axis
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(20.0, 0.0, 0.0),
                item=BIMFactoryElement(type="IfcWall", children=[Box(width=6.0, depth=0.3, height=2.5)]),
                rotation=(45, "Z"),
            )
        ],
    ).build(model)

    # Example 4: Combined translation and rotation
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(30.0, 0.0, 0.0),
                rotation=(30, "Z"),
                item=BIMFactoryElement(type="IfcWall", children=[Cylinder(radius=2.0, height=4.0)]),
            )
        ],
    ).build(model)

    # Example 5: Multiple transformations
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(40.0, 0.0, 0.0),
                item=BIMFactoryElement(type="IfcWall", children=[Box(width=8.0, depth=0.3, height=3.0)]),
                rotation=(90, "Z"),
            )
        ],
    ).build(model)

    # Example 6: Complex transformation with multiple elements
    for i in range(5):
        BIMFactoryElement(
            inst=building,
            children=[
                Transform(
                    translation=(0.0, 10.0 + i * 8.0, 0.0),
                    item=BIMFactoryElement(type="IfcWall", children=[Cube(size=3.0)]),
                    rotation=(i * 15, "Z"),
                )
            ],
        ).build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Transformations model created successfully: {output_file}")


if __name__ == "__main__":
    main()
