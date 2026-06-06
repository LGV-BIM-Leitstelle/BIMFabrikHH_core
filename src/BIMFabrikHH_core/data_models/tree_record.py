"""
Pydantic input record for the generic trees app.

``TreeRecord`` is the public input contract for
:meth:`BIMFabrikHH_core.apps.trees.generic.TreesGenericApp.build_ifc`.
Only fields actually consumed by ``create_tree_element`` belong here.
Property-set templates are passed as Pydantic models (subclasses of
``pydantic.BaseModel``) keyed by their pset name so logging messages can
identify them.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field


class TreeRecord(BaseModel):
    """One tree entry for ``TreesGenericApp.build_ifc``."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = "Baum"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    kronendurchmesser: float = 5.0
    stammdurchmesser: float = 0.6
    detail: int = 1
    segments: int = 8
    baumhoehe: Optional[float] = None
    is_stump: bool = False
    psets: Dict[str, BaseModel] = Field(default_factory=dict)
