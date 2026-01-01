"""
Example: Tree Model using Pydantic Approach
==========================================

This example demonstrates how to create tree objects using
the pydantic-based tree model with configurable property sets.
"""

import ifcopenshell.api.aggregate as aggregate
from ifcfactory import Material

from BIMFabrikHH_core.apps.trees.generic.tree_model_pydantic import TreeBuilder, TreeConfig, TreeModel
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder
from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateSystemTemplates
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree


def create_basic_tree_example():
    """Create a basic tree example with minimal configuration."""

    print("Creating basic tree example...")

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="Basic_Tree_Project",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Basic_Tree_Site",
        building_name="Basic_Tree_Building",
        storey_name="Basic_Tree_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.model3d

    # Create simple tree configuration
    tree_config = TreeConfig(crown_radius=2.0, trunk_radius=0.25, trunk_height=3.5, trunk_segments=8, crown_detail=1)

    # Create tree builder
    tree_builder = TreeBuilder(model, body_context, tree_config)

    # Create tree model without property sets
    tree_model = TreeModel(position=(0, 0, 0), config=tree_config, psets=None)  # No property sets for basic example

    # Build the tree
    tree_element = tree_model.build(model_builder, tree_builder)

    # Aggregate tree under storey
    aggregate.assign_object(model, products=[tree_element], relating_object=storey)

    # Write to file
    output_file = "output/basic_tree_example.ifc"
    model.write(output_file)

    print(f"Basic tree IFC model created successfully: {output_file}")


def create_detailed_tree_example():
    """Create a detailed tree example with property sets and materials."""

    print("Creating detailed tree example...")

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="Detailed_Tree_Project",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Detailed_Tree_Site",
        building_name="Detailed_Tree_Building",
        storey_name="Detailed_Tree_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.model3d

    # Create materials
    trunk_material = Material(name="Tree_Trunk_Material", category="Wood", rgb=(0.44, 0.27, 0.18), transparency=0.0)

    crown_material = Material(
        name="Tree_Crown_Material", category="Vegetation", rgb=(0.13, 0.50, 0.18), transparency=0.1
    )

    # Create detailed tree configuration
    tree_config = TreeConfig(
        crown_radius=3.0,
        trunk_radius=0.4,
        trunk_height=5.0,
        trunk_segments=16,
        crown_detail=2,
        trunk_color=(0.44, 0.27, 0.18),
        crown_color=(0.13, 0.50, 0.18),
        trunk_material=trunk_material,
        crown_material=crown_material,
    )

    # Create property sets
    obj_info = Pset_Objektinformation_Tree(
        baumnummer="TREE_DETAILED_001",
        gattung_deutsch="Buche",
        baumid=101,
        art_deutsch="Rotbuche",
        sorte_deutsch="Fagus sylvatica",
        pflanzjahr=1980,
        kronendurchmesser=6.0,
        stammumfang=0.8,
    )

    dgm_info = Pset_Bauwerk_Tree(strassenname="Beispielstraße")

    psets = {"Pset_Objektinformation": obj_info, "Pset_Bauwerk": dgm_info}

    # Create tree builder
    tree_builder = TreeBuilder(model, body_context, tree_config)

    # Create tree model with property sets
    tree_model = TreeModel(position=(0, 0, 0), config=tree_config, psets=psets)

    # Build the tree
    tree_element = tree_model.build(model_builder, tree_builder)

    # Aggregate tree under storey
    aggregate.assign_object(model, products=[tree_element], relating_object=storey)

    # Write to file
    output_file = "output/detailed_tree_example.ifc"
    model.write(output_file)

    print(f"Detailed tree IFC model created successfully: {output_file}")


def create_multiple_trees_example():
    """Create multiple trees with different configurations."""

    print("Creating multiple trees example...")

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="Multiple_Trees_Project",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Multiple_Trees_Site",
        building_name="Multiple_Trees_Building",
        storey_name="Multiple_Trees_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.model3d

    # Define different tree configurations
    tree_configs = [
        TreeConfig(
            crown_radius=1.5,
            trunk_radius=0.2,
            trunk_height=2.5,
            trunk_segments=6,
            crown_detail=1,
            crown_color=(0.2, 0.6, 0.2),  # Bright green
        ),
        TreeConfig(
            crown_radius=2.5,
            trunk_radius=0.3,
            trunk_height=4.0,
            trunk_segments=10,
            crown_detail=2,
            crown_color=(0.1, 0.4, 0.1),  # Dark green
        ),
        TreeConfig(
            crown_radius=3.5,
            trunk_radius=0.4,
            trunk_height=5.5,
            trunk_segments=12,
            crown_detail=2,
            crown_color=(0.15, 0.5, 0.15),  # Medium green
        ),
    ]

    # Create property sets for different trees
    tree_data = [
        {
            "baumnummer": "TREE_001",
            "gattung_deutsch": "Eiche",
            "baumid": 1,
            "art_deutsch": "Stieleiche",
            "sorte_deutsch": "Quercus robur",
            "pflanzjahr": 1990,
            "kronendurchmesser": 3.0,
            "stammumfang": 0.4,
        },
        {
            "baumnummer": "TREE_002",
            "gattung_deutsch": "Buche",
            "baumid": 2,
            "art_deutsch": "Rotbuche",
            "sorte_deutsch": "Fagus sylvatica",
            "pflanzjahr": 1985,
            "kronendurchmesser": 5.0,
            "stammumfang": 0.6,
        },
        {
            "baumnummer": "TREE_003",
            "gattung_deutsch": "Linde",
            "baumid": 3,
            "art_deutsch": "Sommerlinde",
            "sorte_deutsch": "Tilia platyphyllos",
            "pflanzjahr": 1995,
            "kronendurchmesser": 7.0,
            "stammumfang": 0.8,
        },
    ]

    # Create trees at different positions
    positions = [(0, 0, 0), (8, 0, 0), (16, 0, 0)]

    tree_elements = []

    for i, (config, data, position) in enumerate(zip(tree_configs, tree_data, positions)):
        # Create property sets
        obj_info = Pset_Objektinformation_Tree(**data)
        dgm_info = Pset_Bauwerk_Tree(strassenname=f"Baumstraße {i+1}")

        psets = {"Pset_Objektinformation": obj_info, "Pset_Bauwerk": dgm_info}

        # Create tree builder
        tree_builder = TreeBuilder(model, body_context, config)

        # Create tree model
        tree_model = TreeModel(position=position, config=config, psets=psets)

        # Build the tree
        tree_element = tree_model.build(model_builder, tree_builder)
        tree_elements.append(tree_element)

    # Aggregate all trees under storey
    aggregate.assign_object(model, products=tree_elements, relating_object=storey)

    # Write to file
    output_file = "output/multiple_trees_example.ifc"
    model.write(output_file)

    print(f"Multiple trees IFC model created successfully: {output_file}")


def create_tree_from_data_example():
    """Create a tree from standardized data row."""

    print("Creating tree from data example...")

    # Create model and contexts
    model_builder = IfcModelBuilder()
    model_builder.build_project(
        project_name="Data_Tree_Project",
        coordinate_system=CoordinateSystemTemplates.epsg_25832(),
        coordinate_operation=CoordinateSystemTemplates.get_default_coordinate_operation(),
        site_name="Data_Tree_Site",
        building_name="Data_Tree_Building",
        storey_name="Data_Tree_Storey",
    )

    model = model_builder.model
    storey = model_builder.storey
    body_context = model_builder.model3d

    # Simulate data row from database or CSV
    data_row = {
        "position": (0, 0, 0),
        "kronendurchmesser": 4.5,
        "stammumfang": 0.7,
        "height": 4.2,
        "segments": 12,
        "detail": 2,
    }

    # Create property sets
    obj_info = Pset_Objektinformation_Tree(
        baumnummer="TREE_DATA_001",
        gattung_deutsch="Ahorn",
        baumid=201,
        art_deutsch="Bergahorn",
        sorte_deutsch="Acer pseudoplatanus",
        pflanzjahr=1988,
        kronendurchmesser=4.5,
        stammumfang=0.7,
    )

    dgm_info = Pset_Bauwerk_Tree(strassenname="Datenstraße")

    psets = {"Pset_Objektinformation": obj_info, "Pset_Bauwerk": dgm_info}

    # Create tree from standardized data
    tree_model = TreeModel.from_standardized_data(data_row, psets)

    # Create tree builder with the computed configuration
    tree_builder = TreeBuilder(model, body_context, tree_model.config)

    # Build the tree
    tree_element = tree_model.build(model_builder, tree_builder)

    # Aggregate tree under storey
    aggregate.assign_object(model, products=[tree_element], relating_object=storey)

    # Write to file
    output_file = "output/data_tree_example.ifc"
    model.write(output_file)

    print(f"Data-based tree IFC model created successfully: {output_file}")


def main():
    """Run all tree examples."""

    print("Creating tree examples using pydantic approach...")

    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)

    # Run all examples
    create_basic_tree_example()
    create_detailed_tree_example()
    create_multiple_trees_example()
    create_tree_from_data_example()

    print("\nAll tree examples completed successfully!")


if __name__ == "__main__":
    main()
