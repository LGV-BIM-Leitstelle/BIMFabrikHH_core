#!/usr/bin/env python3
"""
Creates a JSON dictionary based on a BoreholeML codelist,
    (https://schemas.bgr.de/boreholeml/codelists/)

    mapping gml:identifier -> gml:name.

Example:
    python convert_xml_codelist_to_json.py RockNameList.xml -o rock_name_mapping.json
"""

import argparse
from pathlib import Path
import logging
import json
from lxml import etree

logger = logging.getLogger(__name__)

NAMESPACE = {
    "gmx": "http://www.isotc211.org/2005/gmx",
    "gml": "http://www.opengis.net/gml/3.2",
    "bmlcl": "https://schemas.bgr.de/boreholeml/codelists/v2",
}


def get_xml_file_path(input: str) -> Path:
    """Expand input files/directories into a sorted list of XML files."""

    path = Path(input).resolve()

    if path.is_file():
        return path.resolve()
    else: 
        raise OSError


def extract_codelist_identifier(filename: Path) -> str:
    """
    Return the gml:identifier of the outer
    gmx:ML_CodeListDictionary.
    """
    tree = etree.parse(filename)
    root = tree.getroot()

    identifier = root.find("gml:identifier", NAMESPACE)

    if identifier is not None and identifier.text:
        return identifier.text.strip()

    return ""


def extract_codelist_name(filename: Path) -> str:
    """
    Return the gml:name of the outer
    gmx:ML_CodeListDictionary.
    """
    tree = etree.parse(filename)
    root = tree.getroot()

    codelist_name = root.find("gml:identifier", NAMESPACE)

    if codelist_name is not None and codelist_name.text:
        return codelist_name.text.strip()

    return ""


def extract_codelist_entry_pairs(
    filepath: Path,
    warn_on_conflict: bool = True,
) -> dict[str, str]:
    """
    Return a sorted dictionary mapping the gml:identifier of each
    gmx:codeEntry to its gml:name.

    If an identifier occurs multiple times, the first occurrence is kept.
    """
    tree = etree.parse(filepath)
    root = tree.getroot()

    mapping: dict[str, str] = {}

    for entry in root.findall("gmx:codeEntry", NAMESPACE):
        # The actual definition inside the codeEntry
        definition = entry.find("bmlcl:BMLML_CodeDefinition", NAMESPACE)

        if definition is None:
            continue

        # Only direct children are searched, avoiding identifiers/names
        # inside gmx:alternativeExpression.
        identifier = definition.find("gml:identifier", NAMESPACE)
        name = definition.find("gml:name", NAMESPACE)

        if (identifier is not None
            and identifier.text
            and name is not None
            and name.text):
                key = identifier.text.strip()
                value = name.text.strip()

                if key not in mapping:
                    mapping[key] = value
                elif warn_on_conflict and mapping[key] != value:
                    logger.warning(
                        f"Conflicting value for id={key!r} "
                        f"in {filepath}: first={mapping[key]!r}, later={value!r}. "
                        "Keeping the first occurrence."
                        )

    # Sorting the dictionary by keys, ignoring case.
    sorted_dict = dict(sorted(mapping.items(), key=lambda x: x[0].lower()))

    return sorted_dict


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a JSON mapping based on a BoreholeML codelist, mapping gml:identifier to gml:name."
        )
    )
    parser.add_argument(
        "input",
        help="XML file containing a BoreholeML codelist (gmx:ML_CodeListDictionary).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="codelist_mapping.json",
        help="Output JSON file (default: codelist_mapping.json).",
    )
    parser.add_argument(
        "--no-conflict-warnings",
        action="store_true",
        help="Do not warn if a later occurrence has a different value.",
    )

    args = parser.parse_args()

    xml_file = get_xml_file_path(args.input)

    if not xml_file:
            parser.error("No XML file found.")

    codelist_id = extract_codelist_identifier(xml_file)
    codelist_name = extract_codelist_name(xml_file)

    logger.info("Processing %s", xml_file)
    mapping: dict[str, str] = extract_codelist_entry_pairs(
        xml_file,
        warn_on_conflict=not args.no_conflict_warnings,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info(f"Wrote {len(mapping)} unique {codelist_id} ({codelist_name}) entries to {output_path}.")


if __name__ == "__main__":
    main()