"""
Base Interface for Modular Apps

This module provides the base interface that all modular apps should implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import RequestParams


class UIAppInterface(ABC):
    """Clean interface for UI integration with separated steps."""

    @abstractmethod
    def get_data_in_bbox(self, bbox: BoundingBoxParams) -> List[Dict[str, Any]]:
        """Step 1: Get raw data within bounding box."""
        pass

    @abstractmethod
    def process_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 2: Process and clean data."""
        pass

    @abstractmethod
    def create_ifc(self, processed_data: List[Dict[str, Any]], request_params: RequestParams) -> Path:
        """Step 3: Create IFC using existing RequestParams model."""
        pass
