"""
All Primitive Objects Demo with Tree and DGM
============================================

This example demonstrates the usage of ALL available primitive geometry objects
in a row, plus a tree and a 1mx1m Digital Ground Model (DGM).
"""

import os
import time
from pathlib import Path

import pandas as pd
from ifcfactory import (
    BIMFactoryElement,
    Boolean,
    BooleanOperationTypes,
    Box,
    Circle,
    Cube,
    Cylinder,
    ExtrudedNgonAsMesh,
    Extrusion,
    Material,
    MeshRepresentation,
    NgonCylinder,
    Polygon,
    Rect,
    Sphere,
    Style,
    Transform,
)

from BIMFabrikHH_core import BoundingBoxParams, Component, Container, RequestParams
from BIMFabrikHH_core.apps.terrain.basic.app import process_terrain_folder_to_ifc
from BIMFabrikHH_core.apps.trees import DfColTree
from BIMFabrikHH_core.config import get_logger
from BIMFabrikHH_core.config.paths import PathConfig
from BIMFabrikHH_core.core.model_creator.ifc_utils import IfcModelMethods

logger = get_logger()


def create_tree_data():
    """Create sample tree data for demonstration."""
    sample_data = [
        {
            DfColTree.EASTING: 558406.01,
            DfColTree.NORTHING: 5927514.51,
            "kronendurchmesser": 18.0,
            "stammumfang": 1.2,
            "baumnummer": "Demo-Tree-1",
            "gattung_deutsch": "Ahorn",
            "baumid": 1,
            "art_deutsch": "Spitz-Ahorn",
            "sorte_deutsch": "Spitz-Ahorn",
            "strasse": "Primitive Street",
            "stadtteil": "Demo-Stadtteil",
            "bezirk": "Demo-Bezirk",
            "pflanzjahr": 1990,
        }
    ]
    return pd.DataFrame(sample_data)


def create_dgm_data():
    """Create sample DGM data for 1mx1m terrain."""
    # Create a simple 1mx1m terrain with 4 points
    terrain_data = [
        {"x": 0.0, "y": 0.0, "z": 0.0},
        {"x": 1.0, "y": 0.0, "z": 0.1},
        {"x": 1.0, "y": 1.0, "z": 0.2},
        {"x": 0.0, "y": 1.0, "z": 0.15},
    ]
    return pd.DataFrame(terrain_data)


def main():
    """Create a comprehensive IFC model with all primitive objects, tree, and DGM."""
    start_time = time.perf_counter()

    # Create IFC model and setup
    model = IfcModelMethods.create_model("IFC4")
    proj = IfcModelMethods.create_project_entity(model, "all_primitives_project")
    IfcModelMethods.create_units_meter(model)
    IfcModelMethods.create_contexts(model)

    # Create materials for different primitive types
    materials = {
        "box": Material(name="Box_Material", category="Concrete", rgb=(0.8, 0.8, 0.8)),
        "cube": Material(name="Cube_Material", category="Steel", rgb=(0.7, 0.7, 0.9)),
        "cylinder": Material(name="Cylinder_Material", category="Wood", rgb=(0.6, 0.4, 0.2)),
        "sphere": Material(name="Sphere_Material", category="Glass", rgb=(0.2, 0.8, 0.8), transparency=0.3),
        "extrusion": Material(name="Extrusion_Material", category="Plastic", rgb=(0.9, 0.6, 0.6)),
        "ngon": Material(name="Ngon_Material", category="Metal", rgb=(0.8, 0.8, 0.2)),
        "polygon": Material(name="Polygon_Material", category="Stone", rgb=(0.5, 0.5, 0.5)),
    }

    # Create all primitive objects arranged in 4 objects per row
    primitive_elements = []
    spacing = 3.0  # Space between objects
    objects_per_row = 4

    # 1. Box primitive
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Box_Primitive",
            material=materials["box"],
            children=[Box(width=2.0, depth=0.3, height=2.5)],
        )
    )

    # 2. Cube primitive
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Cube_Primitive",
            material=materials["cube"],
            children=[Cube(size=2.0)],
        )
    )

    # 3. Cylinder primitive
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcColumn",
            name="Cylinder_Primitive",
            material=materials["cylinder"],
            children=[Cylinder(radius=1.0, height=3.0)],
        )
    )

    # 4. Sphere primitive
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcDistributionElement",
            name="Sphere_Primitive",
            material=materials["sphere"],
            children=[Sphere(radius=1.2)],
        )
    )

    # 5. Extrusion from Rectangle
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Extrusion_Rect_Primitive",
            material=materials["extrusion"],
            children=[Extrusion(basis=Rect(width=2.5, height=2.0), depth=0.3)],
        )
    )

    # 6. Extrusion from Circle
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcColumn",
            name="Extrusion_Circle_Primitive",
            material=materials["extrusion"],
            children=[Extrusion(basis=Circle(radius=0.8), depth=2.5)],
        )
    )

    # 7. NgonCylinder (8-sided)
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcColumn",
            name="NgonCylinder_Primitive",
            material=materials["ngon"],
            children=[NgonCylinder(radius=0.8, height=2.5, segments=8)],
        )
    )

    # 8. ExtrudedNgonAsMesh (custom polygon)
    custom_ngon = ExtrudedNgonAsMesh(
        basis=[(0, 0, 0), (1, 0, 0), (1.5, 0.5, 0), (1, 1, 0), (0, 1, 0), (0, 0, 0)], height=2.0
    )
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Custom_Ngon_Primitive",
            material=materials["ngon"],
            children=[custom_ngon],
        )
    )

    # 9. Extrusion from Polygon
    polygon_points = [(0, 0), (2, 0), (2.5, 1), (2, 2), (0, 2), (0, 0)]
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Extrusion_Polygon_Primitive",
            material=materials["polygon"],
            children=[Extrusion(basis=Polygon(points=polygon_points), depth=0.3)],
        )
    )

    # 10. MeshRepresentation (custom mesh)
    vertices = [
        (0, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (0, 1, 0),  # bottom
        (0, 0, 1),
        (1, 0, 1),
        (1, 1, 1),
        (0, 1, 1),  # top
    ]
    faces = [
        [0, 1, 2, 3],  # bottom
        [4, 7, 6, 5],  # top
        [0, 4, 5, 1],  # front
        [2, 6, 7, 3],  # back
        [1, 5, 6, 2],  # right
        [0, 3, 7, 4],  # left
    ]
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcDistributionElement",
            name="Mesh_Primitive",
            material=materials["box"],
            children=[MeshRepresentation(vertices=vertices, faces=faces)],
        )
    )

    # 11. Boolean operations example
    # Create a cube with a cylindrical hole
    boolean_example = Boolean(
        operation=BooleanOperationTypes.Difference,
        children=[Cube(size=1.5), Transform(translation=(0.75, 0.75, 0.0), item=Cylinder(radius=0.3, height=2.0))],
    )
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Boolean_Primitive",
            material=materials["cube"],
            children=[boolean_example],
        )
    )

    # 12. Styled primitive with color
    styled_sphere = Style(
        item=Sphere(radius=0.8), rgb=(1.0, 0.0, 0.0), transparency=0.2, cad_layer="Styled_Objects"  # Red
    )
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcDistributionElement",
            name="Styled_Primitive",
            children=[styled_sphere],
        )
    )

    # 13. Transformed primitive
    transformed_box = Transform(
        item=Box(width=1.5, depth=0.3, height=2.0),
        translation=(0.0, 0.0, 1.0),  # Move up by 1m
        rotation=(45.0, "Z"),  # Rotate 45 degrees around Z axis
    )
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcWall",
            name="Transformed_Primitive",
            material=materials["box"],
            children=[transformed_box],
        )
    )

    # 14. Rotated primitive (using Transform with rotation parameter)
    rotated_cylinder = Transform(
        item=Cylinder(radius=0.6, height=2.5),
        translation=(0.0, 0.0, 0.0),  # No translation
        rotation=(30.0, "Z"),  # Rotate 30 degrees around Z axis
    )
    primitive_elements.append(
        BIMFactoryElement(
            type="IfcColumn",
            name="Rotated_Primitive",
            material=materials["cylinder"],
            children=[rotated_cylinder],
        )
    )

    # Position all primitives in 4 objects per row
    positioned_primitives = []
    for i, element in enumerate(primitive_elements):
        row = i // objects_per_row
        col = i % objects_per_row
        x_pos = col * spacing
        y_pos = row * spacing
        positioned_element = Transform(item=element, translation=(x_pos, y_pos, 0.0))
        positioned_primitives.append(positioned_element)

    # Create main project structure with all primitives
    BIMFactoryElement(
        inst=proj,
        children=[
            BIMFactoryElement(
                type="IfcSite",
                name="Primitive_Site",
                children=[
                    BIMFactoryElement(
                        type="IfcBuilding",
                        name="Primitive_Building",
                        children=positioned_primitives,
                    )
                ],
            )
        ],
    ).build(model)

    # Create a simple tree primitive directly in the main model
    logger.info("Creating tree primitive...")

    # Create tree trunk (cylinder)
    tree_trunk = Cylinder(radius=0.3, height=4.0)

    # Create tree crown (sphere)
    tree_crown = Sphere(radius=2.0)

    # Combine trunk and crown with positioning
    tree_assembly = BIMFactoryElement(
        type="IfcBuildingElementProxy",
        name="Demo_Tree",
        children=[
            # Tree trunk at base
            Transform(item=tree_trunk, translation=(0.0, 0.0, 0.0)),
            # Tree crown on top of trunk
            Transform(item=tree_crown, translation=(0.0, 0.0, 4.0)),  # Position crown on top of trunk
        ],
    )

    # Position the tree at the end of the grid
    tree_positioned = Transform(item=tree_assembly, translation=(15.0, 12.0, 0.0))  # Position after the DGM
    positioned_primitives.append(tree_positioned)

    # Create DGM model
    logger.info("Creating DGM model...")
    terrain_folder = Path(__file__).parent
    tif_files = [str(PathConfig.ASSETS / "dgm1_32_558_9270_1_hh_2022.tif")]

    dgm_container = Container(
        containerTitle="Demo_DGM_Container",
        containerId="dgm_demo",
        components={"description": Component(title="Description", value="Demo DGM Component")},
    )

    # Create a 1mx1m DGM by using a very small bounding box
    dgm_request_body = RequestParams(
        bbox=BoundingBoxParams(min_x=9.9756, min_y=53.5522, max_x=9.9757, max_y=53.5523), containers=[dgm_container]
    )

    # Create a simple 1mx1m DGM by processing a small area with higher resolution
    dgm_result = process_terrain_folder_to_ifc(terrain_folder, tif_files, 1, 0.1, dgm_request_body)

    # Also create a simple DGM primitive in the main model for demonstration
    dgm_primitive = BIMFactoryElement(
        type="IfcSite",
        name="DGM_Primitive",
        children=[
            BIMFactoryElement(
                type="IfcBuildingElementProxy",
                name="Simple_DGM_1mx1m",
                children=[Extrusion(basis=Rect(width=1.0, height=1.0), depth=0.1)],
            )
        ],
    )

    # Position the DGM primitive at the end of the grid
    dgm_positioned = Transform(item=dgm_primitive, translation=(15.0, 9.0, 0.0))  # Position after the 4x4 grid
    positioned_primitives.append(dgm_positioned)

    # Write the main model to file
    output_file = os.path.splitext(os.path.basename(__file__))[0] + ".ifc"
    model.write(output_file)

    end_time = time.perf_counter()

    logger.info(f"✓ Successfully created comprehensive primitive objects model: {output_file}")
    logger.info("✓ Tree primitive created in main model")
    logger.info(f"✓ DGM model created: {'Success' if dgm_result else 'Failed'}")
    logger.info(f"Total process time: {end_time - start_time:.2f} seconds")

    print("\nCreated models:")
    print(f"1. Main model with all primitives, tree, and DGM: {output_file}")
    print(f"2. DGM terrain model: {'Success' if dgm_result else 'Failed'}")
    print("\nLayout:")
    print("- All objects aligned along X-axis")
    print("- 4 objects per row (4x4 grid for 14 primitives + 1 DGM + 1 Tree)")
    print("- Single tree with trunk and crown")
    print("- 1mx1m DGM primitive included in main model")
    print("\nPrimitive objects included:")
    print("1. Box, 2. Cube, 3. Cylinder, 4. Sphere, 5. Extrusion (Rect), 6. Extrusion (Circle)")
    print("7. NgonCylinder, 8. ExtrudedNgonAsMesh, 9. Extrusion (Polygon), 10. MeshRepresentation")
    print("11. Boolean operations, 12. Styled objects, 13. Transformed objects, 14. Rotated objects (Transform)")
    print("15. DGM primitive (1mx1m), 16. Tree (trunk + crown)")


if __name__ == "__main__":
    main()
