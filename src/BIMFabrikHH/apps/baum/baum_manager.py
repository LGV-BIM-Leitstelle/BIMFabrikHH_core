import random

import numpy as np
from icosphere import icosphere
from ifcopenshell.api import aggregate, geometry, pset, root, run, spatial
from ifcopenshell.util import placement

from ...core.ifc_snippets import IfcSnippets


class BaumManager:
    def __init__(self):
        self.baumkrone = None
        self.element_baumstamm = None
        self.ifc_snippets = IfcSnippets()
        self.baum = None
        self.idx_baum = 0

    @staticmethod
    def scale_tree_vertices(vertices, radius):
        norms = np.linalg.norm(vertices, axis=1, keepdims=True)
        normalized_vertices = vertices / norms
        scaled_vertices = normalized_vertices * radius

        return scaled_vertices

    def create_tree(self, model, level_of_geom, storey, body, x, y, radius, stammbasis):
        """Create a tree with trunk and crown in IFC model."""

        # Calculate tree dimensions
        kronendurchmesser = radius * 2
        hoehe = int(3.5 if kronendurchmesser < 3 else 1.35 * kronendurchmesser)

        # Generate tree IDs and entities
        tree_id = self._create_tree_id()
        tree_entities = self._create_tree_entities(model, tree_id)

        # Create trunk with placement and material
        self._create_trunk(model, body, tree_entities["trunk"], x, y, stammbasis, hoehe)

        # Create crown with placement and material
        self._create_crown(model, body, tree_entities["crown"], x, y, hoehe, radius, level_of_geom)

        # Set up spatial relationships
        self._setup_tree_relationships(model, storey, tree_entities)

        return tree_entities["tree"]

    def _create_tree_id(self):
        """Generate a unique tree ID."""
        self.idx_baum += 1
        return self.idx_baum

    @staticmethod
    def _create_tree_entities(model, tree_id):
        """Create the main tree entities."""

        main_tree = root.create_entity(model, ifc_class="IfcBuildingElement", name=f"Baum_{tree_id:04d}")
        trunk = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Stamm_{tree_id:04d}")
        crown = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Krone_{tree_id:04d}")

        return {"tree": main_tree, "trunk": trunk, "crown": crown}

    @staticmethod
    def apply_coordinate_offset(vertices, coordinate_offset):
        """
        Apply the coordinate offset to each vertex.
        :param vertices: List of vertices, where each vertex is a tuple (x, y, z).
        :param coordinate_offset: Tuple for the 3D offset (x, y, z).
        :return: List of vertices with the coordinate offset applied.
        """
        return [
            (vertex[0] + coordinate_offset[0], vertex[1] + coordinate_offset[1], vertex[2] + coordinate_offset[2])
            for vertex in vertices
        ]

    def _create_trunk(self, model, body, trunk_entity, x, y, stammbasis, hoehe):
        """Create trunk with geometry, placement and material."""

        vertices_list, faces_list = self.create_trunk_mesh(radius=stammbasis, height=hoehe)

        trunk_representation = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_list], faces=[faces_list], edges=None
        )

        geometry.assign_representation(model, product=trunk_entity, representation=trunk_representation)

        # Set placement
        trunk_matrix = self._create_placement_matrix(x, y, 0)
        geometry.edit_object_placement(model, matrix=trunk_matrix, product=trunk_entity)

        # Assign material
        self.ifc_snippets.assign_color_to_element(model, trunk_representation, "111, 70, 46", 0.0)

    @staticmethod
    def create_trunk_mesh(radius, height, segments=5):
        """Create a simple cylindrical trunk mesh centered at the base."""
        angle_step = 2 * np.pi / segments

        # Bottom vertices for the polygon shape, centered at (0,0,0)
        bottom = [
            (float(radius * np.cos(i * angle_step)), float(radius * np.sin(i * angle_step)), 0) for i in range(segments)
        ]

        # Top vertices are positioned at the height of the trunk
        top = [(float(x), float(y), height) for (x, y, _) in bottom]

        # Combine bottom and top vertices
        vertices = bottom + top

        # Create faces connecting the bottom and top vertices
        faces = []
        for i in range(segments):
            next_i = (i + 1) % segments
            # Side faces
            faces.append((i, next_i, i + segments))
            faces.append((next_i, next_i + segments, i + segments))

        # Add bottom face (connects all bottom vertices in correct order)
        # Note: For proper face orientation, we list vertices in counterclockwise order
        bottom_face = tuple(range(segments - 1, -1, -1))
        faces.append(bottom_face)

        return vertices, faces

    def _create_crown(self, model, body, crown_entity, x, y, hoehe, radius, level_of_geom):
        """Create tree crown with geometry, placement and material."""
        # Generate geometry
        tree_level_of_detail = level_of_geom if level_of_geom else 1
        crown_representation = self._create_crown_representation(model, body, radius, tree_level_of_detail)
        geometry.assign_representation(model, product=crown_entity, representation=crown_representation)

        # Assign material
        self.ifc_snippets.assign_color_to_element(model, crown_representation, "33, 128, 45", 0.0)

        # Set placement with random rotation
        crown_matrix = self._create_crown_placement_matrix(x, y, hoehe)
        run("geometry.edit_object_placement", model, matrix=crown_matrix, product=crown_entity)

    @staticmethod
    def _create_crown_representation(model, body, radius, tree_level_of_detail):
        """Create the crown mesh representation."""
        vertices, faces = icosphere(tree_level_of_detail)
        vertices = BaumManager.scale_tree_vertices(vertices, radius)

        vertices_list = [tuple(float(item) for item in row) for row in vertices]
        faces_list = [tuple(int(item) for item in row) for row in faces]

        return geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_list], faces=[faces_list], edges=None
        )

    @staticmethod
    def _create_placement_matrix(x, y, z):
        """Create a placement matrix for tree elements."""
        matrix = np.eye(4)
        matrix[:, 3][0:3] = (x, y, z)
        return matrix

    @staticmethod
    def _create_crown_placement_matrix(x, y, z):
        """Create a placement matrix for crown with random rotation."""
        matrix = np.eye(4)
        matrix = placement.rotation(random.randint(5, 85), "Z") @ matrix
        matrix = placement.rotation(random.randint(5, 140), "X") @ matrix
        matrix[:, 3][0:3] = (x, y, z)
        return matrix

    @staticmethod
    def _setup_tree_relationships(model, storey, tree_entities):
        """Set up spatial and aggregation relationships for the tree."""

        # Assign to storey
        spatial.assign_container(model, relating_structure=storey, products=[tree_entities["tree"]])

        # Aggregate parts to main tree
        aggregate.assign_object(
            model, relating_object=tree_entities["tree"], products=[tree_entities["crown"], tree_entities["trunk"]]
        )

    def create_tree_alt(self, model, level_of_geom, storey, body, x, y, radius, stammbasis):
        kronendurchmesser = radius * 2
        hoehe = int(3.5 if kronendurchmesser < 3 else 1.35 * kronendurchmesser)

        self.idx_baum += 1
        tree_id = self.idx_baum

        # Create main tree entity first
        self.baum = root.create_entity(model, ifc_class="IfcBuildingElement", name=f"Baum_{tree_id:04d}")

        # Create trunk
        self.element_baumstamm = root.create_entity(
            model, ifc_class="IfcBuildingElementProxy", name=f"Baumstamm_{tree_id:04d}"
        )

        # Create tree crown
        self.baumkrone = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Baumkrone_{tree_id:04d}")

        # add representation for trunk
        representation_baumstamm = geometry.add_wall_representation(
            model, context=body, length=stammbasis, height=hoehe, thickness=stammbasis, offset=-stammbasis / 2
        )
        geometry.assign_representation(model, product=self.element_baumstamm, representation=representation_baumstamm)

        # Placement for trunk
        trunk_matrix = np.eye(4)
        trunk_matrix[:, 3][0:3] = (x, y, 0)
        geometry.edit_object_placement(model, matrix=trunk_matrix, product=self.element_baumstamm)

        # Assign material to trunk
        self.ifc_snippets.assign_color_to_element(model, representation_baumstamm, "111, 70, 46", 0.0)

        # Generate tree crown geometry
        tree_level_of_detail = level_of_geom if level_of_geom else 1
        vertices, faces = icosphere(tree_level_of_detail)
        vertices = BaumManager.scale_tree_vertices(vertices, radius)

        # Convert to proper format for IFC
        vertices_list = [tuple(float(item) for item in row) for row in vertices]
        faces_list = [tuple(int(item) for item in row) for row in faces]

        # Create representation and assign
        representation_tree = geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_list], faces=[faces_list], edges=None
        )
        geometry.assign_representation(model, product=self.baumkrone, representation=representation_tree)

        # Assign material to crown
        self.ifc_snippets.assign_color_to_element(model, representation_tree, "33, 128, 45", 0.0)

        # Placement for crown
        crown_matrix = np.eye(4)
        crown_matrix = placement.rotation(random.randint(5, 85), "Z") @ crown_matrix
        crown_matrix = placement.rotation(random.randint(5, 140), "X") @ crown_matrix
        crown_matrix[:, 3][0:3] = (x, y, hoehe)
        run("geometry.edit_object_placement", model, matrix=crown_matrix, product=self.baumkrone)

        spatial.assign_container(model, relating_structure=storey, products=[self.baum])

        # Aggregate both parts to the main tree entity
        aggregate.assign_object(model, relating_object=self.baum, products=[self.baumkrone, self.element_baumstamm])

    def place_trees_from_df(self, model, df, level_of_geom, storey, body):
        df = df.fillna("")

        for index, tree in df.iterrows():
            radius = float(tree["kronendurchmesser"] / 2)
            if radius < 1:
                radius = 1.0

            umfang = float(tree["stammumfang"])
            if umfang < 0.2:
                umfang = 0.2

            baum = self.create_tree(
                model,
                level_of_geom,
                storey,
                body,
                x=tree["Easting"],
                y=tree["Northing"],
                radius=radius,
                stammbasis=umfang,
            )

            try:
                pset_ifc = pset.add_pset(model, product=baum, name="Pset_Objektinformation")

                pset.edit_pset(
                    model,
                    pset=pset_ifc,
                    properties={
                        "_Baumnummer": tree["baumnummer"],
                        "_Gattung": tree["gattung_deutsch"],
                        "_BaumID": str(tree["baumid"]),
                        "_ArtBaum": tree["art_deutsch"],
                        "_Sorte": tree["sorte_deutsch"],
                        "_Strasse": tree["strasse"],
                        "_Stadtteil": tree["stadtteil"],
                        "_Bezirk": tree["bezirk"],
                        "_Kronendurchmesser": tree["kronendurchmesser"],
                        "_Stammdurchmesser": tree["stammumfang"],
                        "_Pflanzjahr": str(tree["pflanzjahr"]),
                        "_LoG": 100,
                        "_LoI": 100,
                        "_StatusVegetation": "Bestand",
                        "_AufnahmedatumVermessung": "2019-01-01",
                    },
                )
            except Exception as e:
                print(f"Error creating Pset for tree {tree['baumid']}: {e}")

            # Assign the tree to the storey
            # element = model.by_type("IfcBuildingElement")[0]
