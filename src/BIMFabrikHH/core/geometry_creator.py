import ifcopenshell
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.material.add_material
import ifcopenshell.util.placement
import ifcopenshell.util.representation
import numpy as np
import pandas as pd
from ifcopenshell.api import geometry, material, pset, root, type
from ifcopenshell.util.shape_builder import ShapeBuilder, V

from ..default.paths import PathConfig
from .df_columns import DfCol
from .df_parser import DfParser
from .ifc_snippets import IfcSnippets


class GeometryCreator:
    def __init__(self, model):
        self.geometry_creator = None
        self.idx_element = 0
        self.model = model
        self.ifc_snippets = IfcSnippets()
        self.builder = ShapeBuilder(self.model)
        self.data_parser = DfParser()

    def extrude_rect(self, builder, size, height, position):
        return self.builder.extrude(builder.profile(builder.rectangle(size=V(*size))), height, V(*position))

    def create_extrude(self, body, ifc_class="IfcBuildingElementType", location=None):
        dims = {
            "width": 12,
            "depth": 3,
            "height": 0.02,
        }
        shift_to_center = V(-dims["width"] / 2, -dims["depth"] / 2, -dims["height"])
        lod1_solid = self.extrude_rect(self.builder, (dims["width"], dims["depth"]), dims["height"], (0, 0, 0))
        self.builder.translate(lod1_solid, shift_to_center)
        repr_solid = self.builder.get_representation(body, [lod1_solid])
        product_solid = self.model.create_entity(
            ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle_LOD1"
        )
        geometry.assign_representation(self.model, product=product_solid, representation=repr_solid)
        if location:
            aggregate.assign_object(self.model, products=[product_solid], relating_object=location)
        return product_solid

    def create_profil_versetzt(self, body, ifc_class, width, depth, height):
        dims = {
            "width": width,
            "depth": depth,
            "height": height,
        }
        _shift_to_center = V(0.0 / 2, -dims["depth"] / 2, 0.0)

        builder = ifcopenshell.util.shape_builder.ShapeBuilder(self.model)
        outer_curve = builder.polyline([(0.0, 0.0), (width, 0.0), (width, depth), (0.0, depth)], closed=True)
        # inner_curve = builder.circle((50.0, 50.0), radius=10.0)
        profile = builder.profile(outer_curve, name="Arbitrary")
        return profile

    def create_bus_station(self, body, ifc_class="IfcBuildingElementType", location=None, LOD=3):
        dims = {
            "width": 4,
            "depth": 1.61,
            "height": 2.45,
            "frame_width": 0.1,
            "frame_depth": 0.05,
            "thickness": 0.1,
            "seat_width": 2,
            "seat_depth": 0.4,
            "seat_height": 0.5,
        }

        shift_to_center = V(-dims["width"] / 2, -dims["depth"] / 2, 0.0)

        if LOD == 1:
            lod1_solid = self.extrude_rect(self.builder, (dims["width"], dims["depth"]), dims["height"], (0, 0, 0))
            self.builder.translate(lod1_solid, shift_to_center)
            repr_solid = self.builder.get_representation(body, [lod1_solid])
            product_solid = self.model.create_entity(
                ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle_LOD1"
            )
            geometry.assign_representation(self.model, product=product_solid, representation=repr_solid)
            return product_solid

        elif LOD == 2:
            haltestelle_top = self.extrude_rect(
                self.builder,
                (dims["width"], dims["depth"]),
                dims["thickness"],
                (0, 0, dims["height"] - dims["thickness"]),
            )
            side_size, side_height = (0.005, dims["depth"] - 0.1), dims["height"] - (dims["thickness"] + 0.1)
            station_sides = [
                self.extrude_rect(self.builder, side_size, side_height, (x, 0.05, 0.1)) for x in (0, dims["width"])
            ]
            station_back = self.extrude_rect(self.builder, (dims["width"], 0.005), side_height, (0, dims["depth"], 0.1))

            shape_column = self.builder.rectangle(size=V(dims["frame_width"], dims["frame_depth"]))
            columns = [self.builder.profile(shape_column)] + self.builder.mirror(
                shape_column,
                mirror_axes=[V(1, 0), V(0, 1), V(1, 1)],
                mirror_point=V(dims["width"] / 2, dims["depth"] / 2),
                create_copy=True,
            )
            station_columns = [self.builder.extrude(col, dims["height"] - dims["thickness"]) for col in columns]
            station_solid = [haltestelle_top] + station_columns + station_sides + [station_back]

            self.builder.translate(station_solid, shift_to_center)
            repr_solid = self.builder.get_representation(body, station_solid)
            product_solid = self.model.create_entity(
                ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle_LOD2"
            )
            geometry.assign_representation(self.model, product=product_solid, representation=repr_solid)
            return product_solid

        elif LOD == 3:
            haltestelle_top = self.extrude_rect(
                self.builder,
                (dims["width"], dims["depth"]),
                dims["thickness"],
                (0, 0, dims["height"] - dims["thickness"]),
            )
            station_sitz = self.extrude_rect(
                self.builder,
                (dims["seat_width"], dims["seat_depth"]),
                dims["thickness"],
                (dims["width"] - dims["seat_width"], dims["depth"] - dims["seat_depth"], dims["seat_height"]),
            )
            side_size, side_height = (0.005, dims["depth"] - 0.1), dims["height"] - (dims["thickness"] + 0.1)
            station_sides = [
                self.extrude_rect(self.builder, side_size, side_height, (x, 0.05, 0.1)) for x in (0, dims["width"])
            ]
            station_back = self.extrude_rect(self.builder, (dims["width"], 0.005), side_height, (0, dims["depth"], 0.1))
            shape_column = self.builder.rectangle(size=V(dims["frame_width"], dims["frame_depth"]))
            columns = [self.builder.profile(shape_column)] + self.builder.mirror(
                shape_column,
                mirror_axes=[V(1, 0), V(0, 1), V(1, 1)],
                mirror_point=V(dims["width"] / 2, dims["depth"] / 2),
                create_copy=True,
            )
            station_columns = [self.builder.extrude(col, dims["height"] - dims["thickness"]) for col in columns]
            station_solid = [haltestelle_top, station_sitz] + station_columns
            station_glas = station_sides + [station_back]
            self.builder.translate(station_solid, shift_to_center)
            self.builder.translate(station_glas, shift_to_center)
            repr_solid = self.builder.get_representation(body, station_solid)
            repr_glas = self.builder.get_representation(body, station_glas)
            product_solid = self.model.create_entity(
                ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle_Konstruktion"
            )
            product_glas = self.model.create_entity(
                ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle_Glas"
            )
            geometry.assign_representation(self.model, product=product_solid, representation=repr_solid)
            geometry.assign_representation(self.model, product=product_glas, representation=repr_glas)
            glass, white = self.ifc_snippets.create_material(
                self.model, "Glas", "Kategorie_Glas"
            ), self.ifc_snippets.create_material(self.model, "Stahl", "Kategorie_Stahl")
            IfcSnippets.assign_color_to_element(self.model, repr_glas, "204,229,255", 0.7)
            IfcSnippets.assign_color_to_element(self.model, repr_solid, "64,64,64", 0.0)
            for prod, mat in zip([product_glas, product_solid], [glass, white]):
                material.assign_material(self.model, products=[prod], material=mat)
            parent_product = self.model.create_entity(
                ifc_class, GlobalId=ifcopenshell.guid.new(), Name="Bushaltestelle"
            )
            for prod in [product_solid, product_glas]:
                aggregate.assign_object(self.model, relating_object=parent_product, products=[prod])
            if location:
                aggregate.assign_object(self.model, products=[parent_product], relating_object=location)
            return parent_product

    def create_sweep(self, obj_name, laenge, tiefe, hoehe, is_centered=True):
        # Generate the curve
        curve = self.create_profile(laenge, hoehe, is_centered)

        # Create the swept solid from the curve
        swept_curve = self.builder.create_swept_disk_solid(curve, tiefe / 2)

        # Get the context for the body representation
        body = ifcopenshell.util.representation.get_context(self.model, "Model", "Body", "MODEL_VIEW")
        representation = self.builder.get_representation(body, swept_curve)

        product = self.model.create_entity("IfcBuildingElementType", GlobalId=ifcopenshell.guid.new(), Name=obj_name)

        geometry.assign_representation(file=self.model, product=product, representation=representation)

        return product

    def create_profile(self, laenge: float, hoehe: float, is_centered: bool = True):
        # Calculate the starting X-coordinate based on the alignment choice
        start_x = -laenge / 2 if is_centered else 0.0

        # Create the polyline with the calculated starting X-coordinate
        return self.builder.polyline(
            [
                V(start_x, 0.0, 0.0),  # Start at the base (centered or aligned to 0)
                V(start_x, 0.0, hoehe),  # Height of the object
                V(start_x + laenge, 0.0, hoehe),  # Extend along the X-axis
                V(start_x + laenge, 0.0, 0.0),  # End at the base
            ]
        )

    def create_multi_element(self, body, profile, element_name, x, y, z, hoehe, psets=None):
        # # Create our element type. Types do not have an object placement.
        # element_type = run("root.create_entity", model, ifc_class="IfcBuildingElementProxyType", name="Stammbasis")
        # representation = run("geometry.add_profile_representation", model, context=body, profile=profile)
        self.idx_element += 1

        element_baumstamm = root.create_entity(
            self.model, ifc_class="IfcBuildingElementProxy", name="{}_{:04d}".format(element_name, self.idx_element)
        )
        repr_element_instance = geometry.add_profile_representation(
            self.model, context=body, profile=profile, depth=hoehe
        )

        geometry.assign_representation(self.model, product=element_baumstamm, representation=repr_element_instance)

        # Placement
        element_matrix = np.eye(4)

        angle_degrees = self.ifc_snippets.get_angle_from_2pts("5,6", "11,1")
        element_matrix = ifcopenshell.util.placement.rotation(angle_degrees, "Z") @ element_matrix
        # element_matrix = ifcopenshell.util.placement.rotation(45, "Z") @ element_matrix

        element_matrix[:, 3][0:3] = (x, y, z)

        geometry.edit_object_placement(self.model, matrix=element_matrix, product=element_baumstamm)

        # Materials
        self.ifc_snippets.assign_color_to_element(self.model, repr_element_instance, "0.204, 0.204, 0.5", 0.0)
        # run("aggregate.assign_object", model, relating_object=profile_typ, product=element_baumstamm)
        if psets:
            for pset_name in psets:
                self.ifc_snippets.add_psets(self.model, element_baumstamm, pset_name)

        return element_baumstamm

    @staticmethod
    def assign_color(ifc_file, element, rgb_color):
        """Assigns color to an element"""
        print(rgb_color)  # Debugging output

        # Ensure input is cleaned and converted to floats in the 0-1 range
        r, g, b = map(lambda x: int(x) / 255.0, rgb_color.replace(" ", "").split(","))

        color = ifc_file.createIfcColourRgb(None, r, g, b)

        surface_style_rendering = ifc_file.createIfcSurfaceStyleRendering(
            color, None, None, None, None, None, None, None, "NOTDEFINED"
        )

        surface_style = ifc_file.createIfcSurfaceStyle(None, "BOTH", [surface_style_rendering])

        style_assignment = ifc_file.createIfcPresentationStyleAssignment([surface_style])

        # Fix: Check for "RepresentationMaps" instead of "RepresentationMap"
        if hasattr(element, "RepresentationMaps") and element.RepresentationMaps:
            for representation in element.RepresentationMaps[0].Representations:
                if representation.Items:
                    _styled_item = ifc_file.createIfcStyledItem(representation.Items[0], [style_assignment], None)

    def create_standard_profile(
        self, body, profile_name, type_name, profil_xdim, profile_ydim, profile_zdim, color_input, is_centered: bool
    ):
        profile = None

        if profile_name == "Rechteck":
            profile = self.model.create_entity(
                "IfcRectangleProfileDef",
                ProfileName="Profil_{}x{}".format(profil_xdim, profile_ydim),
                ProfileType="AREA",
                XDim=profil_xdim,
                YDim=profile_ydim,
                # placement_zx_axes=((0.0, 0.0, 1.0), (1.0, 0.0, 0.0))
            )
        elif profile_name == "profil_versetzt":

            profile = self.create_profil_versetzt(body, "IfcProfileDef", profil_xdim, profile_ydim, 0.6)

        elif profile_name == "Kreis":
            profile = self.model.create_entity(
                "IfcCircleProfileDef", ProfileName="300C", ProfileType="AREA", Radius=profil_xdim / 2
            )

        elif profile_name == "Oval":
            profile = self.model.create_entity(
                "IfcEllipseProfileDef",
                ProfileName="300E",
                ProfileType="AREA",
                SemiAxis1=profil_xdim,
                SemiAxis2=profile_ydim,
            )

        elif profile_name == "UForm":
            profile = self.model.create_entity(
                "IfcUShapeProfileDef",
                ProfileName="U-EXAMPLE",
                ProfileType="AREA",
                Depth=0.5,
                FlangeWidth=0.5,
                WebThickness=0.05,
                FlangeThickness=0.1,
                FilletRadius=0.0,
                EdgeRadius=0.0,
                FlangeSlope=0.0,
            )

        elif profile_name == "Objekt_Bushaltestelle":
            self.geometry_creator = GeometryCreator(self.model)
            self.geometry_creator.create_bus_station(body)

        else:
            print(f"{profile_name} ist nicht vorhanden")

        element = root.create_entity(self.model, ifc_class="IfcFurnitureType", name=type_name)

        representation = geometry.add_profile_representation(
            self.model, context=body, profile=profile, depth=profile_zdim
        )

        # Materials
        self.ifc_snippets.assign_color_to_element(self.model, representation, color_input, 0.0)

        # self.assign_color(self.model, element, color_input)

        # element_type = run(
        #     "root.create_entity", model, ifc_class="IfcFurnitureType", name="type01"
        # )

        geometry.assign_representation(self.model, product=element, representation=representation)

        if not is_centered:
            # Placement
            element_matrix = np.eye(4)
            # element_matrix = ifcopenshell.util.placement.rotation(random.randint(5, 85), "Z") @ element_matrix
            element_matrix[0, 3] = profil_xdim  # Modify only X component

            geometry.edit_object_placement(self.model, matrix=element_matrix, product=element)

        return element

    def create_mapped_objects(self, body, df, storey, psets=None, extrude_downward=True):

        elements = []
        df_types_dict = {}
        idx_element = 1
        df_types = self.data_parser.aggregate_df(df)
        # print(df_types)
        # df.sort_values(by="Typ", ascending=True)

        for idx, type_name_dict in df_types.iterrows():
            # Beispiel Bushaltestelle
            if type_name_dict["Methode"] == "Objekt_Bushaltestelle":
                self.geometry_creator = GeometryCreator(self.model)
                element_type = self.geometry_creator.create_bus_station(body)
                df_types_dict[type_name_dict["Typ"]] = element_type

            # Beispiel Fussgaengerschutzbuegel
            elif type_name_dict["Methode"] == "Objekt_Sweep_endpunkt":
                self.geometry_creator = GeometryCreator(self.model)
                element_type = self.geometry_creator.create_sweep(
                    type_name_dict[DfCol.TYP],
                    type_name_dict[DfCol.LAENGE],
                    type_name_dict[DfCol.TIEFE],
                    type_name_dict[DfCol.HOEHE],
                    is_centered=False,
                )
                df_types_dict[type_name_dict["Typ"]] = element_type

            # Beispiel Fussgaengerschutzbuegel
            elif type_name_dict["Methode"] == "Objekt_Sweep_mittig":
                self.geometry_creator = GeometryCreator(self.model)
                element_type = self.geometry_creator.create_sweep(
                    type_name_dict[DfCol.TYP],
                    type_name_dict[DfCol.LAENGE],
                    type_name_dict[DfCol.TIEFE],
                    type_name_dict[DfCol.HOEHE],
                )
                df_types_dict[type_name_dict["Typ"]] = element_type

            elif type_name_dict["Methode"] == "profil_versetzt":
                # print(type_name_dict["Methode"])
                element_type = self.create_standard_profile(
                    body=body,
                    profile_name=type_name_dict[DfCol.METHODE],
                    type_name=type_name_dict[DfCol.TYP],
                    profil_xdim=type_name_dict[DfCol.LAENGE],
                    profile_ydim=type_name_dict[DfCol.TIEFE],
                    profile_zdim=type_name_dict[DfCol.HOEHE],
                    color_input=type_name_dict[DfCol.FARBE],
                    is_centered=True,
                )
                df_types_dict[type_name_dict["Typ"]] = element_type

            else:
                element_type = self.create_standard_profile(
                    body=body,
                    profile_name=type_name_dict[DfCol.METHODE],
                    type_name=type_name_dict[DfCol.TYP],
                    profil_xdim=type_name_dict[DfCol.LAENGE],
                    profile_ydim=type_name_dict[DfCol.TIEFE],
                    profile_zdim=type_name_dict[DfCol.HOEHE],
                    color_input=type_name_dict[DfCol.FARBE],
                    is_centered=True,
                )
                df_types_dict[type_name_dict["Typ"]] = element_type

        # für die Psets. Kann später raus aus dieser Methode
        excel_file_path = PathConfig.PROFILES_STADTMOBILIAR
        df_ide = self.data_parser.create_df_from_excel(excel_file_path)

        list_types = []
        for index, row in df.iterrows():
            if row["Typ"] not in list_types:
                idx_element = 1
            list_types.append(row["Typ"])

            x_coordinate = row["Easting"]
            y_coordinate = row["Northing"]

            if pd.notna(row["Midpoint"]):
                x_coordinate, y_coordinate = map(float, row["Referenzpunkt_1"].split(","))

            try:
                angle_degrees = row["Drehung"]
            except KeyError:
                angle_degrees = 0

            obj_name = str(row["IDEbene3"]) + "_" + str(idx_element).zfill(3)
            idx_element += 1

            if row["Einfuegepunkt"] == 2:
                angle_degrees = self.ifc_snippets.get_angle_from_2pts(row["Referenzpunkt_1"], row["Referenzpunkt_2"])

            if row["Einfuegepunkt"] == 3:
                point_a = IfcSnippets.parse_coordinates(row["Referenzpunkt_1"])
                point_c = IfcSnippets.parse_coordinates(row["Referenzpunkt_3"])
                midpoint = (point_a + point_c) / 2
                x_coordinate = midpoint[0]
                y_coordinate = midpoint[1]
                try:
                    angle_degrees = self.ifc_snippets.get_angle_from_2pts(
                        row["Referenzpunkt_1"], row["Referenzpunkt_2"]
                    )
                except Exception as e:
                    print(e)

            try:
                z_coordinate = row["Elevation_dgm"]
            except KeyError:
                z_coordinate = 0.0

            element = root.create_entity(self.model, ifc_class="IfcFurniture", name=obj_name)

            try:
                type.assign_type(self.model, related_objects=[element], relating_type=df_types_dict[row["Typ"]])
            except KeyError:
                type.assign_type(self.model, related_objects=[element], relating_type=df_types_dict[row["Typ"]])

            aggregate.assign_object(self.model, relating_object=storey, products=[element])

            element_matrix = np.eye(4)
            tiefe_value = 0
            if row["Typ"].startswith("Trumme"):
                tiefe_value = row.get(DfCol.LAENGE, 0)  # Get value safely, default to 0 if missing
                element_matrix[1, 3] += tiefe_value / 2  # Move Y-axis by tiefe_value
                # geometry.edit_object_placement(self.model, matrix=element_matrix, product=element)

            # hier to float sonst passiert fehlermeldung
            angle_degrees = float(angle_degrees)
            element_matrix = ifcopenshell.util.placement.rotation(angle_degrees, "Z") @ element_matrix
            if extrude_downward:
                element_matrix[:, 3][0:3] = (x_coordinate, y_coordinate, z_coordinate + 0.02 - row["Hoehe"])
            else:
                element_matrix[:, 3][0:3] = (x_coordinate, y_coordinate, z_coordinate)

            geometry.edit_object_placement(self.model, matrix=element_matrix, product=element)

            if psets:
                for pset_name in psets:
                    self.ifc_snippets.add_psets(self.model, element, pset_name)

            # for element in elements:
            pset_ifc = pset.add_pset(self.model, product=element, name="Pset_Objektinformation")

            idebene1_str = self.data_parser.get_column_value(df_ide, "Blockname", row["Blockname"], "IDEbene1")
            idebene2_str = self.data_parser.get_column_value(df_ide, "Blockname", row["Blockname"], "IDEbene2")
            idebene3_str = self.data_parser.get_column_value(df_ide, "Blockname", row["Blockname"], "IDEbene3")

            pset.edit_pset(
                self.model,
                pset=pset_ifc,
                properties={
                    "_IDEbene1": idebene1_str,
                    "_IDEbene2": idebene2_str,
                    "_IDEbene3": idebene3_str,
                    "_Bemerkung": "undefiniert",
                },
            )

            pset_ifc = pset.add_pset(self.model, product=element, name="Pset_Hyperlink")

            pset.edit_pset(
                self.model,
                pset=pset_ifc,
                properties={
                    "_Hyperlink_001": "www.bim.hamburg.de",
                    "_Hyperlink_001_Bemerkung": "LinkZurHomepageVonBIM.Hamburg",
                },
            )

            elements.append(element)

        return elements
