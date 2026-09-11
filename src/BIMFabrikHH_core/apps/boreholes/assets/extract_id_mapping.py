#!/usr/bin/env python3
"""
Build a JSON dictionary mapping borehole IDs to archive IDs:

    "BDHH_" + ogr:DGK5 + ogr:ARCHIVKURZBEZEICHNUNG -> ogr:ID_STAMMDATEN

from one or more OGR XML files.

Only the value for the first occurrence of each key is kept.

Examples:
    python extract_id_mapping.py ~/Bohrarchiv_HH/BOHRIS_S.P_STAMMDATEN_TG.gml -o id_mapping.json
    python extract_id_mapping.py file1.xml file2.xml
    python extract_id_mapping.py data/*.xml -o id_mapping.json
    python extract_id_mapping.py /path/to/xml_directory -o id_mapping.json

The parser deliberately extracts only the required OGR tags instead of using
a strict XML parser. This also tolerates malformed unrelated tags such as the
"<ogr:>" geometry wrapper appearing in some exports.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

FEATURE_START = re.compile(r"<ogr:featureMember\b")
FEATURE_END = re.compile(r"</ogr:featureMember\s*>")

ID_RE = re.compile(
    r"<ogr:ID_STAMMDATEN\b[^>]*>\s*(.*?)\s*</ogr:ID_STAMMDATEN\s*>",
    re.DOTALL,
)
DGK5_RE = re.compile(
    r"<ogr:DGK5\b[^>]*>\s*(.*?)\s*</ogr:DGK5\s*>",
    re.DOTALL,
)
ARCHIV_RE = re.compile(
    r"<ogr:ARCHIVKURZBEZEICHNUNG\b[^>]*>\s*(.*?)\s*</ogr:ARCHIVKURZBEZEICHNUNG\s*>",
    re.DOTALL,
)


def collect_xml_files(inputs: Iterable[str]) -> list[Path]:
    """Expand input files/directories into a sorted list of XML files."""
    files: set[Path] = set()

    for item in inputs:
        path = Path(item)

        if path.is_file():
            files.add(path.resolve())
        elif path.is_dir():
            files.update(p.resolve() for p in path.glob("*.xml") if p.is_file())
        else:
            logger.warning("Warning: input not found, skipping: %s", item)

    return sorted(files)


def extract_first(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.group(1).strip()


def process_feature(
    feature_text: str,
    mapping: dict[str, str],
    source: Path,
    warn_on_conflict: bool,
) -> None:
    """Extract the required values from one ogr:featureMember."""
    id_stammdaten = extract_first(ID_RE, feature_text)
    dgk5 = extract_first(DGK5_RE, feature_text)
    archiv = extract_first(ARCHIV_RE, feature_text)

    if id_stammdaten is None or dgk5 is None or archiv is None:
        return

    key = "BDHH_" + dgk5 + archiv
    value = id_stammdaten

    if key not in mapping:
        mapping[key] = value
    elif warn_on_conflict and mapping[key] != value:
        logger.warning(
            f"Conflicting value for id={key!r} "
            f"in {source}: first={mapping[key]!r}, later={value!r}. "
            "Keeping the first occurrence."
        )


def parse_file(
    path: Path,
    mapping: dict[str, str],
    warn_on_conflict: bool = True,
) -> None:
    """
    Read a file incrementally and process one featureMember at a time.

    This avoids loading large XML files completely into memory.
    """
    inside_feature = False
    buffer: list[str] = []

    with path.open("r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            if not inside_feature:
                if FEATURE_START.search(line):
                    inside_feature = True
                    buffer = [line]

                    # Also handle a featureMember that starts and ends on one line.
                    if FEATURE_END.search(line):
                        process_feature("".join(buffer), mapping, path, warn_on_conflict)
                        inside_feature = False
                        buffer = []
            else:
                buffer.append(line)

                if FEATURE_END.search(line):
                    process_feature("".join(buffer), mapping, path, warn_on_conflict)
                    inside_feature = False
                    buffer = []

    if inside_feature:
        logger.warning("Unterminated ogr:featureMember at end of %s", path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=("Create a JSON mapping from 'BDHH_' + ogr:DGK5 + ogr:ARCHIVKURZBEZEICHNUNG to ogr:ID_STAMMDATEN.")
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="XML files and/or directories containing XML files.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="archive_id_mapping.json",
        help="Output JSON file (default: archive_id_mapping.json).",
    )
    parser.add_argument(
        "--no-conflict-warnings",
        action="store_true",
        help="Do not warn if a later occurrence has a different value.",
    )

    args = parser.parse_args()

    xml_files = collect_xml_files(args.inputs)
    if not xml_files:
        parser.error("No XML files found.")

    mapping: dict[str, str] = {}

    for xml_file in xml_files:
        logger.info("Processing %s", xml_file)
        parse_file(
            xml_file,
            mapping,
            warn_on_conflict=not args.no_conflict_warnings,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info(f"Wrote {len(mapping)} unique borehole id entries to {output_path}")


if __name__ == "__main__":
    main()
