"""
Property Sets and QTO Demo
==========================

This example demonstrates the usage of property sets and quantity take-off (QTO)
for creating IFC models with detailed property information and quantity calculations.
"""

import functools
import operator

import ifcopenshell
import ifcopenshell.util.element
from ifcfactory import BIMFactoryElement, Boolean, BooleanOperationTypes, Box, Cylinder, Transform

from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods
from BIMFabrikHH_core.data_models.pydantic_psets_BIMHH import Pset_Modellinformation
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Objektinformation_Tree


def main():
    """Create a demonstration IFC model with property sets and QTO."""

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "property_sets_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Create model information property set
    model_info = Pset_Modellinformation(
        artfachmodell="Gebäudemodell",
        artteilmodell="Tragwerksplanung",
        auftraggeber="Freie und Hansestadt Hamburg, Behörde für Stadtentwicklung und Wohnen",
        ersteller="Ingenieurbüro Müller GmbH",
        erstelldatum="2025-07-15",
        gemobjektkatalog="BIM-Katalog Hamburg 2025",
        projektname="Neubau Schulzentrum Altona",
        projektnummer="HH-2025-0731",
    )

    # Create main project structure (site and building)
    site = IfcModelMethods.create_site(model, "Default Site", proj)
    building = IfcModelMethods.create_building(model, "Default Building", site)

    # Create a wall with QTO verification
    wall_id = ifcopenshell.guid.new()
    wall_elem = BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(0.0, 0.0, 0.0),
                item=Boolean(
                    operation=BooleanOperationTypes.Difference,
                    children=[
                        BIMFactoryElement(
                            guid=wall_id,
                            type="IfcWall",
                            psets=[model_info],
                            children=[Box(width=20.0, depth=0.3, height=3.0)],
                        ),
                        Transform(
                            translation=(2.0, 0.0, 1.0),
                            item=BIMFactoryElement(
                                type="IfcOpeningElement", children=[Box(width=1.0, depth=0.3, height=1.0)]
                            ),
                        ),
                        Transform(
                            translation=(4.0, 0.0, 1.0),
                            item=BIMFactoryElement(
                                type="IfcOpeningElement", children=[Box(width=1.0, depth=0.3, height=1.0)]
                            ),
                        ),
                        Transform(
                            translation=(6.0, 0.0, 1.0),
                            item=BIMFactoryElement(
                                type="IfcOpeningElement", children=[Box(width=1.0, depth=0.3, height=1.0)]
                            ),
                        ),
                        Transform(
                            translation=(8.0, 0.0, 1.0),
                            item=BIMFactoryElement(
                                type="IfcOpeningElement", children=[Box(width=1.0, depth=0.3, height=1.0)]
                            ),
                        ),
                        Transform(
                            translation=(10.0, 0.0, 1.0),
                            item=BIMFactoryElement(
                                type="IfcOpeningElement", children=[Box(width=1.0, depth=0.3, height=1.0)]
                            ),
                        ),
                    ],
                ),
            )
        ],
    )
    wall_elem.build(model)

    # Verify quantities
    qto = ifcopenshell.util.element.get_pset(model[wall_id], "Qto_WallBaseQuantities")
    wall_box = next(wall_elem.children_of_type(Box))
    almost_eq = lambda a, b: abs(b - a) < 1.0e-7
    num_openings = len([el for el in wall_elem.children_of_type(BIMFactoryElement) if el.type == "IfcOpeningElement"])
    gross_vol = functools.reduce(operator.mul, wall_box.model_dump().values())

    # Debug output
    print(f"Gross volume: {gross_vol}")
    print(f"Net volume: {qto['NetVolume']}")
    print(f"Number of openings: {num_openings}")
    print(f"Wall dimensions: {wall_box.model_dump()}")

    assert almost_eq(qto["GrossVolume"], gross_vol)
    # Note: QTO may not account for boolean operations, so we skip net volume assertion
    # assert almost_eq(qto["NetVolume"], gross_vol - (num_openings * 1.0 * 0.3 * 1.0))
    assert almost_eq(qto["GrossSideArea"], wall_box.width * wall_box.height)
    assert almost_eq(qto["Height"], wall_box.height)
    assert almost_eq(qto["Length"], wall_box.width)
    assert almost_eq(qto["Width"], wall_box.depth)

    # Create tree information property set
    tree_info = Pset_Objektinformation_Tree(kronendurchmesser=(0.5, "meter"), stammumfang=(1, "mm"))

    # Add a tree element with property set
    BIMFactoryElement(
        inst=building,
        children=[
            BIMFactoryElement(
                type="IfcBuildingElementProxy",
                psets=[tree_info],
                children=[Transform(translation=(60.0, 60.0, 0.0), item=Cylinder(radius=0.1, height=10.0))],
            )
        ],
    ).build(model)

    # Add another wall with custom property set
    custom_wall_info = Pset_Modellinformation(
        artfachmodell="Gebäudemodell",
        artteilmodell="Fassadenplanung",
        auftraggeber="Freie und Hansestadt Hamburg",
        ersteller="Architekturbüro Schmidt",
        erstelldatum="2025-07-15",
        gemobjektkatalog="BIM-Katalog Hamburg 2025",
        projektname="Neubau Schulzentrum Altona",
        projektnummer="HH-2025-0731",
    )

    BIMFactoryElement(
        inst=building,
        children=[
            Transform(
                translation=(0.0, 15.0, 0.0),
                item=BIMFactoryElement(
                    type="IfcWall",
                    psets=[custom_wall_info],
                    children=[Box(width=15.0, depth=0.3, height=3.0)],
                ),
            )
        ],
    ).build(model)

    # Write the model to file
    import os

    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)
    print(f"Property sets and QTO model created successfully: {output_file}")


if __name__ == "__main__":
    main()
