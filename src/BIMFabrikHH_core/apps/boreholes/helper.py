from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree


logger = logging.getLogger(__name__)


UNDEFINED = "undefiniert"

def _adjective_to_attributive(adjective: str) -> str:
    """``schluffig`` → ``schluffiger`` for combined soil names."""
    value = adjective.strip().lower()
    if value.endswith("ig") or value.endswith("isch"):
        return f"{adjective}er"
    return adjective


def _extract_meaning(mapped_symbol: str) -> Optional[str]:
    """Pull ``Meaning`` out of a ``Code (Meaning)`` string."""
    match = re.fullmatch(r".+\s\((.+)\)", mapped_symbol)
    return match.group(1) if match else None


def _clean(value: Any) -> str:
    """Trimmed string for XML text / attribute values (``None`` → ``""``)."""
    if value is None:
        return ""
    return str(value).strip()


def _text(element: Optional[etree._Element], path: str) -> str:
    """Trimmed text of the first ``path`` match below ``element``."""
    if element is None:
        return ""
    return _clean(element.findtext(path))


def _float_or_none(value: Any) -> Optional[float]:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _as_root(source: Union[etree._Element, etree._ElementTree, bytes, str, Path]) -> etree._Element:
    """Normalize the accepted input types to a single XML root element."""
    if isinstance(source, etree._ElementTree):
        return source.getroot()
    if isinstance(source, etree._Element):
        return source
    if isinstance(source, Path):
        return etree.parse(str(source)).getroot()
    if isinstance(source, bytes):
        return etree.fromstring(source)
    if isinstance(source, str):
        return etree.fromstring(source.encode("utf-8"))
    raise TypeError(f"Unsupported BoreholeML source type: {type(source).__name__}")
