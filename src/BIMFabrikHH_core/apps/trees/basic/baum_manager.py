import random
from typing import Any, Dict, List

import ifcopenshell.api.geometry as ifc_geometry
import numpy as np
import pandas as pd
from icosphere import icosphere
from ifcopenshell.api import aggregate, pset, root, run, spatial
from ifcopenshell.util import placement

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.core.geometry.tree_objects import Tree
from BIMFabrikHH_core.core.model_creator import IfcModelBuilder, root
from BIMFabrikHH_core.core.model_creator.ifc_snippets import IfcSnippets
from BIMFabrikHH_core.core.model_creator.pset_utils import assign_psets_to_element
from BIMFabrikHH_core.data_models.pydantic_psets_tree import Pset_Bauwerk_Tree, Pset_Objektinformation_Tree

# Configure logger for this module
logger = get_level_logger("baum_manager")

from .baum_col_names import DfColTree


class BaumManager:
    """
    Manages the creation and placement of tree objects (trunk and crown) in an IFC model.
    Handles geometry, placement, and relationships for tree elements.
    """

    def __init__(self):
        """
        Initialize the BaumManager and supporting objects.
        """
        self.baumkrone = None
        self.element_baumstamm = None
        self.ifc_snippets = IfcSnippets()
        self.baum = None
        self.idx_baum = 0  # Counter for unique tree IDs

    @staticmethod
    def scale_tree_vertices(vertices, radius):
        """
        Scale the vertices of a unit sphere to the desired crown radius.

        Args:
            vertices (np.ndarray): Vertices of the unit sphere.
            radius (float): Desired radius for the crown.

        Returns:
            np.ndarray: Scaled vertices.
        """
        norms = np.linalg.norm(vertices, axis=1, keepdims=True)
        normalized_vertices = vertices / norms
        scaled_vertices = normalized_vertices * radius

        return scaled_vertices

    def create_tree(self, model, level_of_geom, storey, body, x, y, z, radius, stammbasis):
        """
        Create a tree with trunk and crown in the IFC model.

        Args:
            model: The IFC model.
            level_of_geom: Level of geometry detail.
            storey: IFC storey entity.
            body: IFC body context.
            x (float): X coordinate for placement.
            y (float): Y coordinate for placement.
            z (float): Z coordinate (elevation) for placement.
            radius (float): Crown radius.
            stammbasis (float): Trunk base diameter.

        Returns:
            The main tree entity (IfcBuildingElement).
        """
        # Calculate tree dimensions
        kronendurchmesser = radius * 2
        hoehe = int(3.5 if kronendurchmesser < 3 else 1.35 * kronendurchmesser)

        # Generate tree IDs and entities
        tree_id = self._create_tree_id()
        tree_entities = self._create_tree_entities(model, tree_id)

        # Create trunk with placement and material
        self._create_trunk(model, body, tree_entities["trunk"], x, y, z, stammbasis, hoehe)

        # Create crown with placement and material
        self._create_crown(model, body, tree_entities["crown"], x, y, z + hoehe, radius, level_of_geom)

        # Set up spatial relationships
        self._setup_tree_relationships(model, storey, tree_entities)

        return tree_entities["tree"]

    def _create_tree_id(self):
        """
        Generate a unique tree ID for each tree instance.

        Returns:
            int: Unique tree ID.
        """
        self.idx_baum += 1
        return self.idx_baum

    @staticmethod
    def _create_tree_entities(model, tree_id):
        """
        Create the main tree entities (tree, trunk, crown) in the IFC model.

        Args:
            model: The IFC model.
            tree_id (int): Unique tree ID.

        Returns:
            dict: Dictionary with keys 'tree', 'trunk', 'crown' and their corresponding IFC entities.
        """
        main_tree = root.create_entity(model, ifc_class="IfcBuildingElement", name=f"Baum_{tree_id:04d}")
        trunk = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Stamm_{tree_id:04d}")
        crown = root.create_entity(model, ifc_class="IfcBuildingElementProxy", name=f"Krone_{tree_id:04d}")

        return {"tree": main_tree, "trunk": trunk, "crown": crown}

    @staticmethod
    def apply_coordinate_offset(vertices, coordinate_offset):
        """
        Apply the coordinate offset to each vertex.

        Args:
            vertices (list): List of vertices, where each vertex is a tuple (x, y, z).
            coordinate_offset (tuple): Tuple for the 3D offset (x, y, z).

        Returns:
            list: List of vertices with the coordinate offset applied.
        """
        return [
            (vertex[0] + coordinate_offset[0], vertex[1] + coordinate_offset[1], vertex[2] + coordinate_offset[2])
            for vertex in vertices
        ]

    def _create_trunk(self, model, body, trunk_entity, x, y, z, stammbasis, hoehe):
        """
        Create trunk with geometry, placement, and material.

        Args:
            model: The IFC model.
            body: IFC body context.
            trunk_entity: IFC entity for the trunk.
            x (float): X coordinate for placement.
            y (float): Y coordinate for placement.
            z (float): Z coordinate (elevation) for placement.
            stammbasis (float): Trunk base diameter.
            hoehe (float): Height of the trunk.
        """
        # Generate trunk mesh geometry
        vertices_list, faces_list = self.create_trunk_mesh(radius=stammbasis, height=hoehe)

        trunk_representation = ifc_geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_list], faces=[faces_list], edges=None
        )

        ifc_geometry.assign_representation(model, product=trunk_entity, representation=trunk_representation)

        # Set placement
        trunk_matrix = self._create_placement_matrix(x, y, z)
        ifc_geometry.edit_object_placement(model, matrix=trunk_matrix, product=trunk_entity)

        # Assign material (brown color)
        self.ifc_snippets.assign_color_to_element(model, trunk_representation, "111, 70, 46", 0.0)

    @staticmethod
    def create_trunk_mesh(radius, height, segments=5):
        """
        Create a simple cylindrical trunk mesh centered at the base.

        Args:
            radius (float): Radius of the trunk base.
            height (float): Height of the trunk.
            segments (int): Number of segments for the cylinder base.

        Returns:
            tuple: (vertices, faces) for the trunk mesh.
        """
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

    def _create_crown(self, model, body, crown_entity, x, y, z, radius, level_of_geom):
        """
        Create tree crown with geometry, placement, and material.

        Args:
            model: The IFC model.
            body: IFC body context.
            crown_entity: IFC entity for the crown.
            x (float): X coordinate for placement.
            y (float): Y coordinate for placement.
            z (float): Z coordinate for placement.
            radius (float): Crown radius.
            level_of_geom (int): Level of geometry detail.
        """
        # Generate geometry for the crown
        tree_level_of_detail = level_of_geom if level_of_geom else 1
        crown_representation = self._create_crown_representation(model, body, radius, tree_level_of_detail)
        ifc_geometry.assign_representation(model, product=crown_entity, representation=crown_representation)

        # Assign material (green color)
        self.ifc_snippets.assign_color_to_element(model, crown_representation, "33, 128, 45", 0.0)

        # Set placement with random rotation for realism
        crown_matrix = self._create_crown_placement_matrix(x, y, z)
        run("geometry.edit_object_placement", model, matrix=crown_matrix, product=crown_entity)

    @staticmethod
    def _create_crown_representation(model, body, radius, tree_level_of_detail):
        """
        Create the crown mesh representation using an icosphere.

        Args:
            model: The IFC model.
            body: IFC body context.
            radius (float): Crown radius.
            tree_level_of_detail (int): Level of detail for the icosphere.

        Returns:
            IFC mesh representation for the crown.
        """
        vertices, faces = icosphere(tree_level_of_detail)
        vertices = BaumManager.scale_tree_vertices(vertices, radius)

        vertices_list = [tuple(float(item) for item in row) for row in vertices]
        faces_list = [tuple(int(item) for item in row) for row in faces]

        return ifc_geometry.add_mesh_representation(
            model, context=body, vertices=[vertices_list], faces=[[list(face) for face in faces_list]], edges=None
        )

    @staticmethod
    def _create_placement_matrix(x, y, z):
        """
        Create a placement matrix for tree elements.

        Args:
            x (float): X coordinate.
            y (float): Y coordinate.
            z (float): Z coordinate.

        Returns:
            np.ndarray: 4x4 transformation matrix.
        """
        matrix = np.eye(4)
        matrix[:, 3][0:3] = (x, y, z)
        return matrix

    @staticmethod
    def _create_crown_placement_matrix(x, y, z):
        """
        Create a placement matrix for crown with random rotation.

        Args:
            x (float): X coordinate.
            y (float): Y coordinate.
            z (float): Z coordinate.

        Returns:
            np.ndarray: 4x4 transformation matrix with random rotation.
        """
        matrix = np.eye(4)
        matrix = placement.rotation(random.randint(5, 85), "Z") @ matrix
        matrix = placement.rotation(random.randint(5, 140), "X") @ matrix
        matrix[:, 3][0:3] = (x, y, z)
        return matrix

    @staticmethod
    def _setup_tree_relationships(model, storey, tree_entities):
        """
        Set up spatial and aggregation relationships for the tree.

        Args:
            model: The IFC model.
            storey: IFC storey entity.
            tree_entities (dict): Dictionary of tree, trunk, and crown entities.
        """
        # Assign to storey
        spatial.assign_container(model, relating_structure=storey, products=[tree_entities["tree"]])

        # Aggregate parts to main tree
        aggregate.assign_object(
            model, relating_object=tree_entities["tree"], products=[tree_entities["crown"], tree_entities["trunk"]]
        )

    def place_trees_from_df(self, model, df, level_of_geom, storey, body):
        """
        Place multiple trees in the IFC model from a DataFrame.

        Args:
            model: The IFC model.
            df (pd.DataFrame): DataFrame containing tree data.
            level_of_geom (int): Level of geometry detail.
            storey: IFC storey entity.
            body: IFC body context.
        """
        df = df.fillna("")  # Replace NaN with empty string for safety

        for index, tree in df.iterrows():
            try:
                # Calculate radius and trunk circumference, enforce minimums
                try:
                    radius = float(tree["kronendurchmesser"]) / 2
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid kronendurchmesser for tree {tree.get('baumid', index)}: {tree.get('kronendurchmesser')} - using default 2.0m radius"
                    )
                    radius = 2.0

                if radius < 1:
                    radius = 1.0

                try:
                    umfang = float(tree["stammumfang"])
                except (ValueError, TypeError):
                    logger.warning(
                        f"Invalid stammumfang for tree {tree.get('baumid', index)}: {tree.get('stammumfang')} - using default 0.2m"
                    )
                    umfang = 0.2

                if umfang < 0.2:
                    umfang = 0.2

                # Get elevation from DataFrame, default to 0 if not available
                try:
                    elevation = float(tree.get("Elevation", 0))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid elevation for tree {tree.get('baumid', index)} - using default 0")
                    elevation = 0.0

                # Create and place the tree in the model
                baum = self.create_tree(
                    model,
                    level_of_geom,
                    storey,
                    body,
                    x=float(tree["Easting"]),
                    y=float(tree["Northing"]),
                    z=elevation,
                    radius=radius,
                    stammbasis=umfang,
                )
            except Exception as e:
                logger.error(f"Failed to create tree {tree.get('baumid', index)} at index {index}: {e}")
                continue  # Skip this tree and continue with the next one

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
                        "_Pflanzjahr": str(tree[DfColTree.PFLANZJAHR]),
                        "_LoG": 100,
                        "_LoI": 100,
                        "_StatusVegetation": "Bestand",
                        "_AufnahmedatumVermessung": "undefiniert",
                    },
                )
            except Exception as e:
                logger.error(f"Error creating Pset for tree {tree['baumid']}: {e}")

            # Assign the tree to the storey
            # element = model.by_type("IfcBuildingElement")[0]

    def create_trees_from_df(
        self, df: pd.DataFrame, builder: IfcModelBuilder, level_of_geometry: str, psets: Dict[str, Any]
    ) -> List[Any]:
        """
        Create tree entities from DataFrame data.

        Args:
            df (pd.DataFrame): DataFrame containing tree data.
            builder (IfcModelBuilder): IFC model builder instance.
            level_of_geometry (str): Level of geometry detail.
            psets (Dict[str, Any]): Property sets to assign.

        Returns:
            List[Any]: List of created tree entities.
        """
        tree_entities = []

        for _, row in df.iterrows():
            try:
                # Create tree object
                tree = Tree(
                    position=(
                        float(row[DfColTree.EASTING]),
                        float(row[DfColTree.NORTHING]),
                        float(row.get(DfColTree.ELEVATION, 0.0)),
                    ),
                    diameter=float(row.get(DfColTree.STAMMUMFANG_BK, 0.3)),
                    height=float(row.get(DfColTree.HOHE, 10.0)),
                    species=row.get(DfColTree.BAUMART, "Unknown"),
                )

                # Create IFC product
                tree_entity = tree.as_product(builder.model, builder)

                # Assign property sets
                tree_psets = self._create_tree_psets(row, psets)
                assign_psets_to_element(builder.model, tree_entity, tree_psets, None)

                # Assign to site
                if builder.site:
                    spatial.assign_container(builder.model, relating_structure=builder.site, products=[tree_entity])

                tree_entities.append(tree_entity)

            except Exception as e:
                logger.error(f"Error creating Pset for tree {row.get('baumid', 'unknown')}: {e}")
                continue

        return tree_entities

    def _create_tree_psets(self, row: pd.Series, base_psets: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create property sets for a tree entity.

        Args:
            row (pd.Series): Tree data row.
            base_psets (Dict[str, Any]): Base property sets.

        Returns:
            Dict[str, Any]: Property sets for the tree.
        """
        psets = {}

        # Create tree-specific property sets
        try:
            objekt_info = Pset_Objektinformation_Tree(
                baumnummer=row.get(DfColTree.BAUMNUMMER),
                gattung_deutsch=row.get(DfColTree.GATTUNG_DEUTSCH),
                baumid=row.get(DfColTree.BAUMID),
                art_deutsch=row.get(DfColTree.BAUMART),
                sorte_deutsch=row.get(DfColTree.SORTE_DEUTSCH),
                pflanzjahr=row.get(DfColTree.PFLANZJAHR),
                kronendurchmesser=row.get(DfColTree.KRONENDURCHMESSER),
                stammumfang=row.get(DfColTree.STAMMUMFANG_BK),
            )
            psets["Pset_Objektinformation_Tree"] = objekt_info.model_dump(by_alias=True, exclude_unset=True)
        except Exception as e:
            logger.warning(f"Error creating Objektinformation Pset: {e}")

        try:
            bauwerk_info = Pset_Bauwerk_Tree(
                strassenname=row.get(DfColTree.STRASSE),
            )
            psets["Pset_Bauwerk_Tree"] = bauwerk_info.model_dump(by_alias=True, exclude_unset=True)
        except Exception as e:
            logger.warning(f"Error creating Bauwerk Pset: {e}")

        # Add base property sets
        psets.update(base_psets)

        return psets
