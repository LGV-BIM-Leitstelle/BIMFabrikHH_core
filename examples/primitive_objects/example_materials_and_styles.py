"""
Materials and Styles Demo
========================

This example demonstrates the usage of materials and styling
for creating IFC models with different materials and visual properties.
"""

from ifcfactory import BIMFactoryElement, Box, Cube, Cylinder, Material, Style, Transform

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with materials and styles."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "materials_styles_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)
    psets = []
    # Define materials
    concrete = Material(name="CON01", category="concrete", rgb=(0.5, 0.5, 0.5))
    wood = Material(
        name="WOOD01",
        category="wood",
        rgb=(0.65, 0.50, 0.30),
    )
    glass = Material(name="GLASS01", category="glass", rgb=(0.6, 0.9, 0.8), transparency=0.6)
    steel = Material(name="STEEL01", category="steel", rgb=(0.7, 0.7, 0.7))

    # Create main project structure (site and building entities)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Add a red cube wall with styling
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                vec=(0.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[Style(item=Cube(size=10.0), rgb=(0.8, 0.1, 0.1))],
                ),
            )
        ],
    ).build(model)

    # Add a wooden wall with material
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                vec=(12.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[Cube(size=10.0)],
                    material=wood,
                ),
            )
        ],
    ).build(model)

    # Add a glass wall with transparency
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                vec=(24.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[Cylinder(radius=5.0, height=10.0)],
                    material=glass,
                ),
            )
        ],
    ).build(model)

    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                vec=(36.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[Box(width=8.0, depth=0.3, height=3.0)],
                    material=concrete,
                    psets=psets,
                    qsets=True,
                ),
            )
        ],
    ).build(model)

    # Add a steel wall with styling
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                vec=(48.0, 0.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    children=[Style(item=Box(width=6.0, depth=0.2, height=4.0), rgb=(0.8, 0.8, 0.8))],
                ),
            )
        ],
    ).build(model)

    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Materials and styles model created successfully: {output_file}")


if __name__ == "__main__":
    main()
