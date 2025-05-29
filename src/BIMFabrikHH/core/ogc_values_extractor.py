from pydantic import ValidationError

from ..pydantic_models.params_tree import ModelParams


def extract_project_info(containers):
    """
    Extract project name, site name, and building name from containers.
    Returns a tuple: (project_name, site_name, building_name)
    """
    project_name = "IfcProjectName"
    site_name = "SiteName"
    building_name = "BuildingName"

    for container in containers or []:
        if container.containerId == "Projektinformationen" and container.components:
            for component in container.components.values():
                if component.title == "Projektname" and component.value:
                    project_name = component.value
                elif component.title == "IfcSite" and component.value:
                    site_name = component.value
                elif component.title == "IfcBuilding" and component.value:
                    building_name = component.value

    return project_name, site_name, building_name


def extract_level_of_geometry(containers) -> int:
    """
    Extract the level of geometry from containers.
    Returns: level_of_geom (int)
    """
    level_of_geom = 1

    for container in containers or []:
        if container.containerId == "level_of_geometry":
            component = container.components.get("level_of_geom")
            if component and component.value is not None:
                level_of_geom = component.value

    return level_of_geom


# def extract_level_of_geometry(containers) -> int:
#     """
#     Extract the level of geometry from containers and validate it using Pydantic.
#     Returns: level_of_geom (int)
#     """
#     level_of_geom = 1
#
#     for container in containers or []:
#         if container.containerId == "level_of_geometry":
#             component = container.components.get("level_of_geom")
#             if component and component.value is not None:
#                 try:
#                     # Validate using ModelParams
#                     validated = ModelParams(level_of_geom=component.value)
#                     level_of_geom = validated.level_of_geom
#                 except ValidationError as e:
#                     print(f"Validation failed: {e}")
#
#     return level_of_geom


def extract_psets_basepoint(containers):
    pset_groups = {}
    for container in containers:
        if container.containerId.startswith("Pset_"):
            pset_data = {}
            for comp_key, comp_val in container.components.items():
                pset_data[comp_val.title] = comp_val.value
            pset_groups[container.containerId] = pset_data
    return pset_groups
