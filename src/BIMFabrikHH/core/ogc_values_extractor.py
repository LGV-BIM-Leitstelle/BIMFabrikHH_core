def extract_project_info(containers):
    """
    Extract project name, site name, and building name from containers.
    Returns a tuple: (project_name, site_name, building_name)
    """
    project_name = "IfcProjectName"
    site_name = "SiteName"
    building_name = "BuildingName"

    for container in containers or []:
        if container.containerTitle == "Pset_ProjectInformation" and container.components:
            for component in container.components.values():
                if component.title == "project_name" and component.value:
                    project_name = component.value
                elif component.title == "site_name" and component.value:
                    site_name = component.value
                elif component.title == "building_name" and component.value:
                    building_name = component.value

    return project_name, site_name, building_name


def extract_level_of_geometry(containers):
    """
    Extract the level of geometry from containers.
    Returns: level_of_geom (int)
    """
    level_of_geom = 1

    for container in containers or []:
        if container.containerTitle == "Level_Of_Geometry" and container.components:
            for component in container.components.values():
                if component.title == "level_of_geom" and component.value is not None:
                    level_of_geom = component.value

    return level_of_geom
