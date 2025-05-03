import tempfile
from pathlib import Path

import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
from ifcopenshell.api import aggregate, context, georeference, run
from ifcopenshell.api.root import create_entity

from ..default.paths import PathConfig
from ..pydantic_models.pydantic_georeferencing import GeoreferencingData, ProjectedCRSData


class IfcFileCreator:
    @staticmethod
    def create_model(ifc_schema):
        model = ifcopenshell.file(schema=ifc_schema.upper())
        return model

    @staticmethod
    def create_project(model, project_name, site_name, building_name):
        project = run("root.create_entity", model, ifc_class="IfcProject", name=project_name)
        site = create_entity(model, ifc_class="IfcSite", name=site_name)
        aggregate.assign_object(model, products=[site], relating_object=project)

        building = None
        if building_name:
            building = create_entity(model, ifc_class="IfcBuilding", name=building_name)
            aggregate.assign_object(model, relating_object=site, products=[building])

        return project, site, building

    @staticmethod
    def create_floorplans(model, building, floorplans):
        floorplans_instances = []
        for floorplan_name in floorplans:
            floorplan = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name=floorplan_name)
            aggregate.assign_object(model, relating_object=building, products=[floorplan])
            floorplans_instances.append(floorplan)

        return floorplans_instances

    @staticmethod
    def create_units_meter(model):
        length = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT")
        area = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="AREAUNIT")
        run("unit.assign_unit", model, units=[length, area])

    @staticmethod
    def create_representations(model):
        model3d = run("context.add_context", model, context_type="Model")
        plan = context.add_context(model, context_type="Plan")
        body = context.add_context(
            model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
        )

        return model3d, plan, body

    @staticmethod
    def create_georeference(model):
        georeference.add_georeferencing(model)

    @staticmethod
    def edit_georeference(model):
        georeference.edit_georeferencing(
            model,
            coordinate_operation={
                "Name": "EPSG:25832",
                "Description": "UTM zone 32N (ETRS89 / UTM zone 32N)",
                "GeodeticDatum": "ETRS89",
                "VerticalDatum": "DHHN2016",
                "MapProjection": "Transverse Mercator",
                "MapZone": "32",
            },
            projected_crs={
                "Eastings": 3570605.5513,
                "Northings": 5937434.3470,
                "XAxisAbscissa": 0.0,
                "XAxisOrdinate": 0.0,
                "Scale": 1.0,
            },
        )

    @staticmethod
    def get_ifc_georeferencing(model) -> GeoreferencingData:
        conversion = None
        try:
            conversion = model.by_type("IfcMapConversion")[0]
        except Exception as _e:
            pass

        if not conversion:
            project = model.by_type("IfcProject")[0]
            conversion = ifcopenshell.util.element.get_pset(project, "ePSet_MapConversion")

        if conversion:
            georeferencing_data = GeoreferencingData(
                Eastings=getattr(conversion, "Eastings", None),
                Northings=getattr(conversion, "Northings", None),
                OrthogonalHeight=getattr(conversion, "OrthogonalHeight", None),
                XAxisAbscissa=getattr(conversion, "XAxisAbscissa", None),
                XAxisOrdinate=getattr(conversion, "XAxisOrdinate", None),
                Scale=getattr(conversion, "Scale", None),
                # SourceCRS=getattr(conversion, 'SourceCRS', None),
                # TargetCRS=getattr(conversion, 'TargetCRS', None)
            )
            return georeferencing_data
        else:
            return GeoreferencingData()

    @staticmethod
    def get_projected_crs(model) -> ProjectedCRSData:
        try:
            projected_crs = model.by_type("IfcProjectedCRS")[0]

            projected_crs_data = ProjectedCRSData(
                Name=getattr(projected_crs, "Name", None),
                Description=getattr(projected_crs, "Description", None),
                GeodeticDatum=getattr(projected_crs, "GeodeticDatum", None),
                VerticalDatum=getattr(projected_crs, "VerticalDatum", None),
                MapProjection=getattr(projected_crs, "MapProjection", None),
                MapZone=getattr(projected_crs, "MapZone", None),
                MapUnit=getattr(projected_crs, "MapUnit", None),
            )
            return projected_crs_data
        except Exception:
            return ProjectedCRSData()

    @staticmethod
    def save_ifc_in_memory(model):
        # Create a temporary file to hold the IFC data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ifc") as temp_file:
            model.write(temp_file.name)
            # Get the temporary file path
            temp_file_path = temp_file.name

        # Read the contents of the temporary file
        with open(temp_file_path, "rb") as file:
            # Read the bytes from the file
            ifc_bytes = file.read()

        return ifc_bytes

    @staticmethod
    def save_ifc_file(model, filename):
        output_path = Path(PathConfig.OUTPUT) / filename
        print(output_path)
        model.write(output_path)
