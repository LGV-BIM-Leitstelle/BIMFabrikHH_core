import logging
from typing import Any, Dict, List, Tuple

from .config import ogc_extractor_settings

logger = logging.getLogger(__name__)


def extract_project_info(containers: List[Any]) -> Tuple[str, str, str]:
    """
    Extract project name, site name, and building name from containers.

    Args:
        containers: List of container objects with project info.

    Returns:
        tuple[str, str, str]: (project_name, site_name, building_name)
    """
    project_name = ogc_extractor_settings.DEFAULT_PROJECT_NAME
    site_name = ogc_extractor_settings.DEFAULT_SITE_NAME
    building_name = ogc_extractor_settings.DEFAULT_BUILDING_NAME

    for container in containers or []:
        if container.containerId == ogc_extractor_settings.PROJECT_INFO_CONTAINER_ID and container.components:
            for component in container.components.values():
                if component.title == ogc_extractor_settings.PROJECT_NAME_TITLE and component.value:
                    project_name = component.value
                elif component.title == ogc_extractor_settings.SITE_NAME_TITLE and component.value:
                    site_name = component.value
                elif component.title == ogc_extractor_settings.BUILDING_NAME_TITLE and component.value:
                    building_name = component.value

    return project_name, site_name, building_name


def extract_level_of_geometry(containers: List[Any]) -> int:
    """
    Extract the level of geometry from containers.

    Args:
        containers: List of container objects with geometry info.

    Returns:
        int: level_of_geom (default_data 1 if not found)
    """
    level_of_geom = ogc_extractor_settings.DEFAULT_LEVEL_OF_GEOMETRY

    for container in containers or []:
        if container.containerId == ogc_extractor_settings.LEVEL_OF_GEOMETRY_CONTAINER_ID:
            component = container.components.get(ogc_extractor_settings.LEVEL_OF_GEOMETRY_COMPONENT_KEY)
            if component and component.value is not None:
                level_of_geom = component.value

    return level_of_geom


def extract_psets_basepoint(containers: List[Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract property sets for the base point from containers.

    Args:
        containers: List of container objects with property set info.

    Returns:
        dict: Dictionary of property set groups for the base point.
    """
    pset_groups = {}
    for container in containers:
        if container.containerId.startswith(ogc_extractor_settings.PSET_CONTAINER_PREFIX):
            pset_data = {}
            for comp_key, comp_val in container.components.items():
                pset_data[comp_val.title] = comp_val.value
            pset_groups[container.containerId] = pset_data
            # Debug logging for Pset_Hyperlink
            if container.containerId == "Pset_Hyperlink":
                logger.info(f"DEBUG: Pset_Hyperlink extracted data: {pset_data}")
                logger.info(f"DEBUG: Number of fields: {len(pset_data)}")
                logger.info(f"DEBUG: Keys: {list(pset_data.keys())}")
    return pset_groups
