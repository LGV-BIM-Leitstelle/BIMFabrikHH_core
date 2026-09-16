"""
Internal helpers to be used for borehole processing.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from lxml import etree


logger = logging.getLogger(__name__)


UNDEFINED = "undefiniert"

def _adjective_to_attributive(adjective: str) -> str:
    """``schluffig`` → ``schluffiger`` for combined soil names."""
    value = adjective.strip().lower()
    if value.endswith("ig") or value.endswith("isch"):
        return f"{adjective}er"
    return adjective


def _extract_meaning(mapped_symbol: str) -> str | None:
    """Pull ``Meaning`` out of a ``Code (Meaning)`` string."""
    match = re.fullmatch(r".+\s\((.+)\)", mapped_symbol)
    return match.group(1) if match else None


def _clean(value: Any) -> str:
    """Trimmed string for XML text / attribute values (``None`` → ``""``)."""
    if value is None:
        return ""
    return str(value).strip()


def _text(element: etree._Element | None, path: str) -> str:
    """Trimmed text of the first ``path`` match below ``element``."""
    if element is None:
        return ""
    return _clean(element.findtext(path))


def _top_level_comma_parts(text: str) -> list[str]:
    """Split on commas that are not inside ``(...)``."""
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
            buf.append(char)
        elif char == ")":
            depth = max(0, depth - 1)
            buf.append(char)
        elif char == "," and depth == 0:
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
        else:
            buf.append(char)
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def _float_or_none(value: Any) -> float | None:
    text = _clean(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _split_rock_code(rock_code: str) -> tuple[str, str]:
    """Split a DIN ``rockCode`` into main and secondary components.

    Two notations occur in the Hamburg service: ``F(s4, hz4, ht2)`` puts the
    secondary components in brackets, ``mS, yy`` lists co-equal components.

    Args:
        rock_code: Raw ``bml:rockCode`` value.

    Returns:
        ``(hauptgemengteil, nebengemengteil)``; both may be empty.
    """
    text = _clean(rock_code)
    if not text:
        return ("", "")

    tokens = _top_level_comma_parts(text)
    if not tokens:
        return ("", "")

    if any("(" in token for token in tokens):
        mains: list[str] = []
        sides: list[str] = []
        for token in tokens:
            bracket = re.match(r"^\(?([^()]+)\)?\((.*)\)\s*$", token)
            if bracket:
                main = bracket.group(1).strip()
                if main:
                    mains.append(main)
                inner = bracket.group(2).strip()
                if inner:
                    sides.extend(part.strip() for part in inner.split(",") if part.strip())
            else:
                mains.append(token)
        return (", ".join(mains), ", ".join(sides))

    return (tokens[0], ", ".join(tokens[1:]))