from typing import List, Literal, Optional, Tuple

import ifcopenshell
import ifcopenshell.api.aggregate as aggregate
import ifcopenshell.api.context as context
import ifcopenshell.api.georeference as georeference
import ifcopenshell.api.root as root
from ifcopenshell.api import run

from BIMFabrikHH_core.data_models.pydantic_georeferencing import CoordinateOperation, CoordinateSystem

# Provide direct alias to make patching in unit tests easier
create_entity = root.create_entity


class IfcModelMethods:
    """
    Utility class for creating and managing IFC models.
    Provides static methods for common IFC operations.
    """

    @staticmethod
    def create_model(ifc_schema: Literal["IFC2X3", "IFC4", "IFC4X3"]) -> ifcopenshell.file:
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
    def create_project_entity(model: ifcopenshell.file, project_name: str) -> ifcopenshell.entity_instance:
        """
        Create an IfcProject entity.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            project_name (str): Name for the project entity.

        Returns:
            ifcopenshell.entity_instance: The created project entity.
        """
        return run("root.create_entity", model, ifc_class="IfcProject", name=project_name)

    @staticmethod
    def create_site(
        model: ifcopenshell.file, site_name: str, project: Optional[ifcopenshell.entity_instance] = None
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcSite entity and assign to project if provided.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            site_name (str): Name for the site entity.
            project (ifcopenshell.entity_instance, optional): Project entity to assign the site to.

        Returns:
            ifcopenshell.entity_instance: The created site entity.
        """
        site = create_entity(model, ifc_class="IfcSite", name=site_name)
        if project is not None:
            aggregate.assign_object(model, products=[site], relating_object=project)
        return site

    @staticmethod
    def create_building(
        model: ifcopenshell.file, building_name: str, site: Optional[ifcopenshell.entity_instance] = None
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcBuilding entity and assign to site if provided.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            building_name (str): Name for the building entity.
            site (ifcopenshell.entity_instance, optional): Site entity to assign the building to.

        Returns:
            ifcopenshell.entity_instance: The created building entity.
        """
        building = create_entity(model, ifc_class="IfcBuilding", name=building_name)
        if site is not None:
            aggregate.assign_object(model, relating_object=site, products=[building])
        return building

    @staticmethod
    def create_storey(
        model: ifcopenshell.file, storey_name: str, building: Optional[ifcopenshell.entity_instance] = None
    ) -> ifcopenshell.entity_instance:
        """
        Create an IfcBuildingStorey entity and assign to building if provided.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            storey_name (str): Name for the storey entity.
            building (ifcopenshell.entity_instance, optional): Building entity to assign the storey to.

        Returns:
            ifcopenshell.entity_instance: The created storey entity.
        """
        storey = create_entity(model, ifc_class="IfcBuildingStorey", name=storey_name)
        if building is not None:
            aggregate.assign_object(model, relating_object=building, products=[storey])
        return storey

    @staticmethod
    def create_floorplans(
        model: ifcopenshell.file, building: ifcopenshell.entity_instance, floorplans: List[str]
    ) -> List[ifcopenshell.entity_instance]:
        """
        Create building storeys (floorplans) in the IFC model.

        Args:
            model (ifcopenshell.file): The IFC model instance.
            building (ifcopenshell.entity_instance): The building entity to assign floorplans to.
            floorplans (List[str]): List of floorplan names.

        Returns:
            List[ifcopenshell.entity_instance]: List of created floorplan entities.
        """
        floorplans_instances = []
        for floorplan_name in floorplans:
            floorplan = run("root.create_entity", model, ifc_class="IfcBuildingStorey", name=floorplan_name)
            aggregate.assign_object(model, relating_object=building, products=[floorplan])
            floorplans_instances.append(floorplan)

        return floorplans_instances

    @staticmethod
    def create_units_meter(model: ifcopenshell.file) -> None:
        """
        Add SI units (meter for length and area) to the IFC model.

        Args:
            model (ifcopenshell.file): The IFC model instance.
        """
        length = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT")
        area = ifcopenshell.api.run("unit.add_si_unit", model, unit_type="AREAUNIT")
        run("unit.assign_unit", model, units=[length, area])

    @staticmethod
    def create_contexts(
        model: ifcopenshell.file,
    ) -> Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
        """
        Create 3D and plan contexts for the IFC model.

        Args:
            model (ifcopenshell.file): The IFC model instance.

        Returns:
            Tuple[ifcopenshell.entity_instance, ifcopenshell.entity_instance, ifcopenshell.entity_instance]:
                (model3d, plan, body) context entities.
        """
        model3d = run("context.add_context", model, context_type="Model")
        plan = context.add_context(model, context_type="Plan")
        body = context.add_context(
            model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=model3d
        )

        return model3d, plan, body

    @staticmethod
    def create_georeference(model: ifcopenshell.file) -> None:
        """
        Add empty georeferencing entities to the IFC model (IFC4).
        This only creates the entities; you must set parameters with edit_georeference.
        """

        # Create the georeferencing entities
        georeference.add_georeferencing(model)

        if not model.by_type("IfcProjectedCRS"):
            import logging

            logging.warning("Failed to create IfcProjectedCRS entity")
        if not model.by_type("IfcMapConversion"):
            import logging

            logging.warning("Failed to create IfcMapConversion entity")

    @staticmethod
    def edit_georeference(
        model: ifcopenshell.file, coordinate_system: CoordinateSystem, coordinate_operation: CoordinateOperation
    ) -> None:
        """
        Edit georeferencing information in the IFC model using the provided CoordinateSystem and CoordinateOperation.
        """

        georeference.edit_georeferencing(
            model,
            projected_crs=coordinate_system.model_dump(by_alias=True),
            coordinate_operation=coordinate_operation.model_dump(by_alias=True),
        )
