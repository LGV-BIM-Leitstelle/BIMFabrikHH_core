"""
Base interface for BIMFabrikHH record-builder apps.

All current apps (trees, terrain, city) follow the **record-builder**
pattern: ``build_ifc(records, *, request_params, ...) -> Path``. The
protocol below describes that contract structurally — any class exposing
a compatible ``build_ifc`` counts as a record builder without needing
to inherit from it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Protocol, runtime_checkable


@runtime_checkable
class RecordBuilderApp(Protocol):
    """Structural contract for record-builder apps.

    Any class (``@staticmethod`` or instance method) that exposes
    ``build_ifc`` with a records-first signature returning a ``Path``
    satisfies this protocol without needing to inherit it.
    """

    def build_ifc(self, records: List[Any], **kwargs: Any) -> Path:  # noqa: D401
        """Build an IFC file from pre-prepared records and return its path."""
        ...
