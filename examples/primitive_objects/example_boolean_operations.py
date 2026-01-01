"""
Boolean Operations Demo
======================

This example demonstrates the usage of boolean operations
for creating complex geometry by combining and subtracting primitive objects.
"""

from ifcfactory import (
    BIMFactoryElement,
    Boolean,
    BooleanOperationTypes,
    Box,
    Cube,
    Extrusion,
    Material,
    Rect,
    Transform,
)

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods


def main():
    """Create a demonstration IFC model with boolean operations."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "boolean_operations_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Define materials
    wood = Material(
        name="WOOD01",
        category="wood",
        rgb=(0.65, 0.50, 0.30),
    )

    # Create main project structure (site and building entities)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Example 1: Wall with rectangular opening using profile difference
    BIMFactoryElement(
        inst=building,
        children=[
            BIMFactoryElement(
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
        ],
    ).build(model)

    # Example 2: Wooden wall with cubic opening
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(12.0, 0.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        BIMFactoryElement(type="IfcWall", children=[Cube(size=10.0)], material=wood),
                        Transform(
                            translation=(5.0, 5.0, 5.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=5.0)]),
                        ),
                    ],
                ),
            )
        ],
    ).build(model)

    # Example 3: Wall with multiple openings
    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(24.0, 0.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        BIMFactoryElement(type="IfcWall", children=[Cube(size=10.0)]),
                        Transform(
                            translation=(2.0, 2.0, 2.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=2.0)]),
                        ),
                        Transform(
                            translation=(6.0, 2.0, 2.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=2.0)]),
                        ),
                        Transform(
                            translation=(2.0, 6.0, 2.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=2.0)]),
                        ),
                        Transform(
                            translation=(6.0, 6.0, 2.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=2.0)]),
                        ),
                    ],
                ),
            )
        ],
    ).build(model)

    # Example 4: Complex wall with multiple openings
    wall_elem = BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(0.0, 15.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        BIMFactoryElement(type="IfcWall", children=[Box(width=20.0, depth=0.3, height=3.0)]),
                        Transform(
                            translation=(2.0, -0.5, 1.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=1.0)]),
                        ),
                        Transform(
                            translation=(4.0, -0.5, 1.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=1.0)]),
                        ),
                        Transform(
                            translation=(6.0, -0.5, 1.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=1.0)]),
                        ),
                        Transform(
                            translation=(8.0, -0.5, 1.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=1.0)]),
                        ),
                        Transform(
                            translation=(10.0, -0.5, 1.0),
                            item=BIMFactoryElement(type="IfcOpeningElement", children=[Cube(size=1.0)]),
                        ),
                    ],
                ),
            )
        ],
    )
    wall_elem.build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Boolean operations model created successfully: {output_file}")


if __name__ == "__main__":
    main()
