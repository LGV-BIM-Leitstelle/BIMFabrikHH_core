"""
Complex Assemblies Demo
======================

This example demonstrates the usage of complex assemblies
for creating IFC models with furniture and multi-component objects.
"""

from ifcfactory import BIMFactoryElement, Box, Transform

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with complex assemblies."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "complex_assemblies_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Create main project structure (site and building entities)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Add chair type to project
    chair_type = BIMFactoryElement(
        type="IfcFurnishingElementType",
        name="CHAIR01",
        children=[
            # Chair legs
            Transform(translation=(-0.05, -0.05, 0.0), item=Box(width=0.10, depth=0.10, height=0.40)),
            Transform(translation=(0.35, -0.05, 0.0), item=Box(width=0.10, depth=0.10, height=0.40)),
            Transform(translation=(-0.05, 0.35, 0.0), item=Box(width=0.10, depth=0.10, height=0.40)),
            Transform(translation=(0.35, 0.35, 0.0), item=Box(width=0.10, depth=0.10, height=0.40)),
            # Chair seat
            Transform(translation=(-0.05, -0.05, 0.40), item=Box(width=0.50, depth=0.50, height=0.05)),
            # Chair back legs
            Transform(translation=(-0.05, 0.35, 0.45), item=Box(width=0.10, depth=0.10, height=0.50)),
            Transform(translation=(0.35, 0.35, 0.45), item=Box(width=0.10, depth=0.10, height=0.50)),
            # Chair back
            Transform(translation=(-0.05, 0.30, 0.75), item=Box(width=0.50, depth=0.05, height=0.20)),
        ],
    )

    BIMFactoryElement(inst=model.by_type("IfcProject")[0], children=[chair_type]).build(model)

    # Create multiple chair instances with rotation
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(i, 0.0, 0.0),
                item=BIMFactoryElement(type="IfcFurnishingElement", children=[chair_type]),
                rotation=(180, "Z"),
            )
            for i in range(1, 21)
        ],
    ).build(model)

    # Create a table type
    table_type = BIMFactoryElement(
        type="IfcFurnishingElementType",
        name="TABLE01",
        children=[
            # Table legs
            Transform(translation=(-0.4, -0.4, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(0.4, -0.4, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(-0.4, 0.4, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(0.4, 0.4, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            # Table top
            Transform(translation=(-0.5, -0.5, 0.75), item=Box(width=1.0, depth=1.0, height=0.05)),
        ],
    )

    BIMFactoryElement(inst=model.by_type("IfcProject")[0], children=[table_type]).build(model)

    # Create table instances
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(i * 2.0, 10.0, 0.0),
                item=BIMFactoryElement(type="IfcFurnishingElement", children=[table_type]),
            )
            for i in range(5)
        ],
    ).build(model)

    # Create a desk type with drawers
    desk_type = BIMFactoryElement(
        type="IfcFurnishingElementType",
        name="DESK01",
        children=[
            # Desk legs
            Transform(translation=(-0.6, -0.3, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(0.6, -0.3, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(-0.6, 0.3, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            Transform(translation=(0.6, 0.3, 0.0), item=Box(width=0.08, depth=0.08, height=0.75)),
            # Desk top
            Transform(translation=(-0.7, -0.4, 0.75), item=Box(width=1.4, depth=0.8, height=0.05)),
            # Drawer unit
            Transform(translation=(-0.6, -0.3, 0.0), item=Box(width=0.4, depth=0.6, height=0.7)),
            # Drawer handles
            Transform(translation=(-0.5, -0.25, 0.35), item=Box(width=0.2, depth=0.02, height=0.02)),
            Transform(translation=(-0.5, -0.15, 0.35), item=Box(width=0.2, depth=0.02, height=0.02)),
        ],
    )

    BIMFactoryElement(inst=model.by_type("IfcProject")[0], children=[desk_type]).build(model)

    # Create desk instances
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(i * 3.0, 20.0, 0.0),
                item=BIMFactoryElement(type="IfcFurnishingElement", children=[desk_type]),
                rotation=(90, "Z"),
            )
            for i in range(3)
        ],
    ).build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Complex assemblies model created successfully: {output_file}")


if __name__ == "__main__":
    main()
