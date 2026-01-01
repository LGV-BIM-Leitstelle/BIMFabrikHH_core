"""
Ngon Cylinders Demo
===================

This example demonstrates the usage of ngon cylinders
for creating IFC models with polygonal cylindrical shapes.
"""

from ifcfactory import BIMFactoryElement, Cylinder, Material, NgonCylinder, Transform

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with ngon cylinders."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "ngon_cylinders_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Define materials
    glass = Material(name="GLASS01", category="glass", rgb=(0.6, 0.9, 0.8), transparency=0.6)
    concrete = Material(name="CON01", category="concrete", rgb=(0.5, 0.5, 0.5))

    # Create main project structure (site and building entities)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Example 1: Basic ngon cylinder (8 segments)
    BIMFactoryElement(
        inst=building,
        children=[
            BIMFactoryElement(
                type="IfcWall",
                material=glass,
                children=[Transform(translation=(0.0, 0.0, 0.0), item=NgonCylinder(radius=5.0, height=10.0))],
            )
        ],
    ).build(model)

    # Example 2: Ngon cylinder with more segments (16 segments)
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(15.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    material=concrete,
                    children=[NgonCylinder(radius=3.0, height=8.0, segments=16)],
                ),
            )
        ],
    ).build(model)

    # Example 3: Ngon cylinder with few segments (6 segments)
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(30.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[NgonCylinder(radius=4.0, height=6.0, segments=6)],
                ),
            )
        ],
    ).build(model)

    # Example 4: Regular cylinder for comparison
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(45.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    material=concrete,
                    children=[Cylinder(radius=5.0, height=10.0)],
                ),
            )
        ],
    ).build(model)

    # Example 5: Multiple ngon cylinders with different configurations
    for i in range(5):
        BIMFactoryElement(
            inst=building,
            children=[
                Transform(
                    translation=(0.0, 15.0 + i * 8.0, 0.0),
                    item=BIMFactoryElement(
                        type="IfcWall",
                        children=[NgonCylinder(radius=2.0 + i * 0.5, height=5.0, segments=8 + i * 2)],
                    ),
                )
            ],
        ).build(model)

    # Example 6: Ngon cylinder with glass material
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(60.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    material=glass,
                    children=[NgonCylinder(radius=6.0, height=12.0, segments=12)],
                ),
            )
        ],
    ).build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Ngon cylinders model created successfully: {output_file}")


if __name__ == "__main__":
    main()
