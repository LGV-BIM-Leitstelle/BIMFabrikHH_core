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
    print(f"PROJECT_ROOT: {PathConfig.PROJECT_ROOT}")
    print(f"ASSETS: {PathConfig.ASSETS}")
    print(f"OUTPUT: {PathConfig.OUTPUT}")
    print(f"EXAMPLES: {PathConfig.EXAMPLES}")
    print(f"SRC: {PathConfig.SRC}")
    print(f"TESTS: {PathConfig.TESTS}")
    print(f"TEMP: {PathConfig.TEMP}")
    print(f"CONFIG: {PathConfig.CONFIG}")
