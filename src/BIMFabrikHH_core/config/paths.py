"""
Path configuration for BIMFabrikHH.

This module defines all the important paths used throughout the application.
"""

from pathlib import Path


class PathConfig:
    """
    Configuration class for managing file paths and constants.
    """

    _PROJECT_ROOT = Path(__file__).resolve().parents[3]

    PARENT = Path(__file__).parent
    PROJECT_ROOT = _PROJECT_ROOT
    EXAMPLES = _PROJECT_ROOT / "examples"
    ASSETS = EXAMPLES / "assets"
    OUTPUT = _PROJECT_ROOT / "output"
    SRC = _PROJECT_ROOT / "src"
    TESTS = _PROJECT_ROOT / "tests"
    TEMP = _PROJECT_ROOT / "temp"
    # Use package location for config when installed, fallback to dev path
    CONFIG = Path(__file__).parent  # This is always BIMFabrikHH_core/config/


if __name__ == "__main__":
    from BIMFabrikHH_core.config.logging_config import get_logger

    logger = get_logger("paths")

    logger.info("PROJECT_ROOT: %s", PathConfig.PROJECT_ROOT)
    logger.info("ASSETS: %s", PathConfig.ASSETS)
    logger.info("OUTPUT: %s", PathConfig.OUTPUT)
    logger.info("EXAMPLES: %s", PathConfig.EXAMPLES)
    logger.info("SRC: %s", PathConfig.SRC)
    logger.info("TESTS: %s", PathConfig.TESTS)
    logger.info("TEMP: %s", PathConfig.TEMP)
    logger.info("CONFIG: %s", PathConfig.CONFIG)
