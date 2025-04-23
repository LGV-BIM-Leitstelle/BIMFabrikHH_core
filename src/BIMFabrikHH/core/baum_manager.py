import random

import numpy as np
from icosphere import icosphere
from ifcopenshell.api import run, geometry, aggregate, pset, root
from ifcopenshell.util import placement, representation

from .ifc_snippets import IfcSnippets


class BaumManager:
    def __init__(self):
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
        kronendurchmesser = radius * 2
        hoehe = int(3.5 if kronendurchmesser < 3 else 1.35 * kronendurchmesser)

        self.idx_baum += 1
        creation_method = 2

        if creation_method == 1:

            profile = model.create_entity(
                "IfcRectangleProfileDef",
                ProfileName="Baum",
                ProfileType="AREA",
                XDim=stammbasis,
                YDim=stammbasis,
                placement_zx_axes=((0.0, 0.0, 1.0), (1.0, 0.0, 0.0)),
            )
            element_baumstamm = root.create_entity(
                model,
                ifc_class="IfcBuildingElementProxy",
                name="Baumstamm_{:04d}".format(self.idx_baum),
            )
            representation_baumstamm = geometry.add_profile_representation(
                model, context=body, profile=profile, depth=hoehe
            )
            geometry.assign_representation(
                model,
                product=element_baumstamm,
                representation=representation_baumstamm,
            )
            aggregate.assign_object(model, relating_object=storey, products=[element_baumstamm])

        elif creation_method == 2:
            element_baumstamm = root.create_entity(
                model,
                ifc_class="IfcBuildingElementProxy",
            )
            representation_baumstamm = geometry.add_wall_representation(
                model,
                context=body,
                length=stammbasis,
                height=hoehe,
                thickness=stammbasis,
                offset=-stammbasis / 2,
            )
            geometry.assign_representation(
                model,
                product=element_baumstamm,
                representation=representation_baumstamm,
            )
            aggregate.assign_object(model, relating_object=storey, products=[element_baumstamm])
        elif creation_method == 3:
            element_baumstamm = root.create_entity(
                model,
                ifc_class="IfcBuildingElementProxy",
                name="Baumstamm_{:04d}".format(self.idx_baum),
            )
            rectangle = model.createIfcRectangleProfileDef(ProfileType="AREA", XDim=stammbasis, YDim=stammbasis)
            direction = model.createIfcDirection((0.0, 0.0, 1.0))
            extrusion = model.createIfcExtrudedAreaSolid(SweptArea=rectangle, ExtrudedDirection=direction, Depth=hoehe)
            body = representation.get_context(model, "Model", "Body", "MODEL_VIEW")
            representation_baumstamm = model.createIfcShapeRepresentation(
                ContextOfItems=body,
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[extrusion],
            )
            geometry.assign_representation(
                model,
                product=element_baumstamm,
                representation=representation_baumstamm,
            )
        else:
            x_length = stammbasis / 2
            element_baumstamm = root.create_entity(
                model,
                ifc_class="IfcBuildingElementProxy",
            )
            representation_baumstamm = geometry.create_2pt_wall(
                model,
                element=element_baumstamm,
                context=body,
                p1=(0, 0),
                p2=(x_length, x_length),
                elevation=0,
                height=hoehe,
                thickness=stammbasis,
                is_si=True,
            )

            element_matrix = np.eye(4)
            # element_matrix = ifcopenshell.util.placement.rotation(random.randint(5, 85), "Z") @ element_matrix
            element_matrix[:, 3][0:3] = (-x_length, -x_length, 10)
            geometry.edit_object_placement(model, matrix=element_matrix, product=element_baumstamm)

            geometry.assign_representation(
                model,
                product=element_baumstamm,
                representation=representation_baumstamm,
            )
            aggregate.assign_object(model, relating_object=storey, products=[element_baumstamm])

        # Placement
        element_matrix = np.eye(4)
        element_matrix[:, 3][0:3] = (x, y, 0)

        geometry.edit_object_placement(model, matrix=element_matrix, product=element_baumstamm)

        # Materials
        self.ifc_snippets.assign_color_to_element(model, representation_baumstamm, "111, 70, 46", 0.0)

        # Tree Icosphere
        if level_of_geom:
            nu = level_of_geom
        else:
            nu = 1  # nu = random.randint(1, 10)

        vertices, faces = icosphere(nu)
        vertices = BaumManager.scale_tree_vertices(vertices, radius)

        vertices_list = [tuple(float(item) for item in row) for row in vertices]
        faces_list = [tuple(int(item) for item in row) for row in faces]

        self.baum = root.create_entity(
            model,
            ifc_class="IfcBuildingElement",
            name="Baum_{:04d}".format(self.idx_baum),
        )

        self.baumkrone = root.create_entity(
            model,
            ifc_class="IfcBuildingElementProxy",
            name="Baumkrone_{:04d}".format(self.idx_baum),
        )

        representation_tree = geometry.add_mesh_representation(
            model,
            context=body,
            vertices=[vertices_list],
            faces=[faces_list],
            edges=None,
        )
        geometry.assign_representation(model, product=self.baumkrone, representation=representation_tree)
        aggregate.assign_object(model, relating_object=storey, products=[self.baumkrone])

        self.ifc_snippets.assign_color_to_element(model, representation_tree, "33, 128, 45", 0.0)

        # Placement
        element_matrix = np.eye(4)
        element_matrix = placement.rotation(random.randint(5, 85), "Z") @ element_matrix
        element_matrix = placement.rotation(random.randint(5, 140), "X") @ element_matrix
        element_matrix[:, 3][0:3] = (x, y, hoehe)
        run(
            "geometry.edit_object_placement",
            model,
            matrix=element_matrix,
            product=self.baumkrone,
        )
        #
        # aggregate.assign_object(
        #     model, relating_object=self.baum, products=[self.baumkrone]
        # )
        # aggregate.assign_object(
        #     model, relating_object=self.baum, products=[element_baumstamm]
        # )

        # model.createIfcRelAggregates(
        #     GlobalId=ifcopenshell.guid.new(),
        #     # OwnerHistory=model.by_type("IfcOwnerHistory")[0],
        #     RelatingObject=self.baum,
        #     RelatedObjects=[element_baumstamm, self.baumkrone],
        # )

    def place_trees_from_df(self, model, df, level_of_geom, storey, body):

        df = df.fillna("")

        for index, tree in df.iterrows():
            radius = float(tree["kronendurchmesser"] / 2)
            if radius < 1:
                radius = 1.0

            umfang = float(tree["stammumfang"])
            if umfang < 0.2:
                umfang = 0.2

            self.create_tree(
                model,
                level_of_geom,
                storey,
                body,
                x=tree["Easting"],
                y=tree["Northing"],
                radius=radius,
                stammbasis=umfang,
            )
            pset_ifc = pset.add_pset(
                model,
                product=self.baumkrone,
                name="Pset_Objektinformation",
            )

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
