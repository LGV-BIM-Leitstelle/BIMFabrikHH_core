from pathlib import Path
from typing import Literal, Optional

import ifcopenshell.util.element
import ifcopenshell.util.placement
import ifcopenshell.util.representation
from ifcopenshell.api import aggregate, context, georeference, run
from ifcopenshell.api.root import create_entity

from ..data_models.pydantic_georeferencing import GeoreferencingData, ProjectedCRSData
from ..default_data.paths import PathConfig


class IfcFileCreator:
    """
    Utility class for creating, managing, and saving IFC models.
    Provides static methods for common IFC operations.
    """

    @staticmethod
    def create_model(ifc_schema: Literal["IFC2X3", "IFC4", "IFC4X3"]):
        """
        Create a new IFC model with the specified schema.

        Args:
            ifc_schema (str): The IFC schema version (e.g., 'IFC4').

        Returns:
            ifcopenshell.file: The created IFC model.
        """
        model = ifcopenshell.file(schema=ifc_schema)
        return model

    @staticmethod
    def create_project(model, project_name: str, site_name: str, building_name: Optional[str] = None):
        """
        Create a project, site, and optionally a building in the IFC model.

        Args:
            model: The IFC model.
            project_name (str): Name of the project.
            site_name (str): Name of the site.
            building_name (Optional[str]): Name of the building (optional).

        Returns:
            Tuple: (project, site, building) entities.
        """
        project = run("root.create_entity", model, ifc_class="IfcProject", name=project_name)
        site = create_entity(model, ifc_class="IfcSite", name=site_name)
        aggregate.assign_object(model, products=[site], relating_object=project)

        building = None
        if building_name:
            building = create_entity(model, ifc_class="IfcBuilding", name=building_name)
            aggregate.assign_object(model, relating_object=site, products=[building])

        return project, site, building

    @staticmethod
    def create_floorplans(model, building, floorplans: list[str]):
        """
        Create building storeys (floorplans) in the IFC model.

        Args:
            model: The IFC model.
            building: The building entity.
            floorplans (list[str]): List of floorplan names.

        Returns:
            list: List of created floorplan entities.
        """
        floorplans_instances = []
        for floorplan_name in floorplans:
            floorplan = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name=floorplan_name)
            aggregate.assign_object(model, relating_object=building, products=[floorplan])
            floorplans_instances.append(floorplan)

        return floorplans_instances

    @staticmethod
    def create_units_meter(model):
        """
        Add SI units (meter for length and area) to the IFC model.

        Args:
            model: The IFC model.
        """
        length = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT")
        area = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="AREAUNIT")
        run("unit.assign_unit", model, units=[length, area])

    @staticmethod
    def create_representations(model):
        """
        Create 3D and plan contexts for the IFC model.

        Args:
            model: The IFC model.

        Returns:
            Tuple: (model3d, plan, body) context entities.
        """
        model3d = run("context.add_context", model, context_type="Model")
        plan = context.add_context(model, context_type="Plan")
        body = context.add_context(
            model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
        )

        return model3d, plan, body

    @staticmethod
    def create_georeference(model):
        """
        Add georeferencing information to the IFC model.

        Args:
            model: The IFC model.
        """
        georeference.add_georeferencing(model)

    @staticmethod
    def edit_georeference(model):
        """
        Edit georeferencing information in the IFC model with default_data values.

        Args:
            model: The IFC model.
        """
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
        """
        Retrieve georeferencing data from the IFC model.

        Args:
            model: The IFC model.

        Returns:
            GeoreferencingData: Georeferencing information.
        """
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
        """
        Retrieve projected CRS data from the IFC model.

        Args:
            model: The IFC model.

        Returns:
            ProjectedCRSData: Projected CRS information.
        """
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
    def save_ifc_in_memory(model) -> Optional[bytes]:
        """
        Save IFC model to memory using a local temporary directory.

        Args:
            model: The IFC model.

        Returns:
            Optional[bytes]: The IFC file as bytes, or None if saving fails.
        """
        try:
            # Creating a local temp directory if it doesn't exist
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)

            # Creating a temporary file in our local directory
            temp_file = temp_dir / "temp.ifc"

            # Writing the model
            model.write(str(temp_file))

            # Reading the file back as bytes
            with open(temp_file, "rb") as f:
                ifc_bytes = f.read()

            # Cleaning up
            temp_file.unlink()

            return ifc_bytes

        except Exception as e:
            print(f"Error saving IFC model to memory: {str(e)}")
            import traceback

            traceback.print_exc()
            return None

    @staticmethod
    def save_ifc_file(model, filename: str) -> Path:
        """
        Safely save IFC file to disk with proper path handling.

        Args:
            model: The IFC model.
            filename (str): The filename to save as.

        Returns:
            Path: The path to the saved IFC file.

        Raises:
            IOError: If saving fails or if filename is empty.
        """
        if not filename:
            raise IOError("Filename cannot be empty")

        try:
            # Creating output directory if it doesn't exist
            output_path = Path(PathConfig.OUTPUT)
            output_path.mkdir(parents=True, exist_ok=True)

            # Ensuring the filename is safe
            safe_filename = Path(filename).name  # Get just the filename part, no path
            file_path = output_path / safe_filename

            model.write(str(file_path))
            return file_path

        except Exception as e:
            raise IOError(f"Failed to save IFC file {filename}: {str(e)}") from e
