"""
Base interfaces for BIMFabrikHH apps.

Two archetypes exist:

* ``BboxSourceApp`` (future) — three-step pipeline that ingests geo data given
  a bounding box and produces an IFC file (city GML, terrain TIF, ...). Today
  the ``CityModularApp`` plays this role through the legacy ``UIAppInterface``
  ABC below.
* ``RecordBuilderApp`` — one-shot builder that takes already-prepared typed
  records and writes an IFC file (trees, basepoints, ...). Implemented as a
  ``typing.Protocol`` so any class exposing ``build_ifc(records, ...)`` counts
  as one, without inheritance.

``UIAppInterface`` is kept for the city app until it is migrated.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Protocol, runtime_checkable

from BIMFabrikHH_core.data_models.params_bbox import BoundingBoxParams
from BIMFabrikHH_core.data_models.params_tree import RequestParams


class UIAppInterface(ABC):
    """Legacy 3-step contract for bbox-sourced apps (kept until full migration)."""

    @abstractmethod
    def get_data_in_bbox(self, bbox: BoundingBoxParams) -> List[Dict[str, Any]]:
        """Step 1: Get raw data within bounding box."""

    @abstractmethod
    def process_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Step 2: Process and clean data."""

    @abstractmethod
    def create_ifc(self, processed_data: List[Dict[str, Any]], request_params: RequestParams) -> Path:
        """Step 3: Create IFC using existing RequestParams model."""


@runtime_checkable
class RecordBuilderApp(Protocol):
    """Structural contract for record-builder apps.

    Any class (``@staticmethod`` or instance method) that exposes ``build_ifc``
    with a records-first signature returning a ``Path`` satisfies this
    protocol without needing to inherit it.
    """

    def build_ifc(self, records: List[Any], **kwargs: Any) -> Path:  # noqa: D401
        """Build an IFC file from pre-prepared records and return its path."""
        ...
