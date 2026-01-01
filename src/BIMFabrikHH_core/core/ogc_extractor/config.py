"""
Configuration module for the OGC Values Extractor.

This module handles all configuration settings for the OGC extractor, loading
base values from JSON and allowing environment variable overrides using Pydantic Settings.
"""

import json

from pydantic_settings import BaseSettings

from BIMFabrikHH_core.config.logging_colors import get_level_logger
from BIMFabrikHH_core.config.paths import PathConfig

# Configure logger for this module
logger = get_level_logger("ogc_extractor_config")


# Check for JSON configuration file
config_path = PathConfig.CONFIG / "ogc_extractor.json"
logger.info(f"JSON config loaded: {config_path.exists()}")

if not config_path.exists():
    logger.warning(f"JSON configuration file not found at: {config_path}")
    logger.warning("Please ensure the ogc_extractor.json file exists in the config directory.")


class OGCExtractorSettings(BaseSettings):
    """
    OGC Extractor configuration settings.

    Loads base configuration from JSON file and allows environment variable overrides.
    """

    # Default values for project information
    DEFAULT_PROJECT_NAME: str
    DEFAULT_SITE_NAME: str
    DEFAULT_BUILDING_NAME: str

    # Default value for level of geometry
    DEFAULT_LEVEL_OF_GEOMETRY: int

    # Container IDs
    PROJECT_INFO_CONTAINER_ID: str
    LEVEL_OF_GEOMETRY_CONTAINER_ID: str
    PSET_CONTAINER_PREFIX: str

    # Component titles for project information
    PROJECT_NAME_TITLE: str
    SITE_NAME_TITLE: str
    BUILDING_NAME_TITLE: str

    # Component keys
    LEVEL_OF_GEOMETRY_COMPONENT_KEY: str

    model_config = {"env_file_encoding": "utf-8"}


def load_settings() -> OGCExtractorSettings:
    """
    Load settings from JSON configuration file.

    This function reads the OGC extractor configuration from a JSON file located
    in the config directory. The configuration includes default project names,
    container IDs, and component mappings for the OGC API integration.

    Returns:
        OGCExtractorSettings: Configuration object with all settings loaded.

    Raises:
        FileNotFoundError: If the configuration file does not exist at the expected path.
        ValueError: If the JSON file contains invalid JSON syntax.
        RuntimeError: If there are other errors during configuration loading.

    """
    config_path_local = PathConfig.CONFIG / "ogc_extractor.json"

    if not config_path_local.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path_local}")

    try:
        with open(config_path_local, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Filter out documentation fields (starting with _) before validation
        filtered_data = {k: v for k, v in json_data.items() if not k.startswith("_")}

        return OGCExtractorSettings(**filtered_data)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")
    except Exception as e:
        raise RuntimeError(f"Error loading configuration: {e}")


# Initialize settings
ogc_extractor_settings = load_settings()
