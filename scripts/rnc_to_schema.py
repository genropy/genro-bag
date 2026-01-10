#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Convert RNG schema to Bag schema using SchemaBuilder.

This script parses RELAX NG (RNG) schema files and converts them
to a Bag schema using SchemaBuilder, then serializes as MessagePack.

Usage:
    python scripts/rnc_to_schema.py <input> <output> [--void tag1,tag2,...]

Arguments:
    input           Path to RNG file or directory containing RNG files
    output          Path for the output MessagePack file (.bag.mp)
    --void          Comma-separated list of void (self-closing) element names

Example:
    python scripts/rnc_to_schema.py src/genro_bag/builders/schemas/html5 schemas/html5_schema.bag.mp --void br,hr,img,input,meta,link
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# RELAX NG namespace
RNG_NS = "{http://relaxng.org/ns/structure/1.0}"


def extract_elements_from_rng(rng_file: Path) -> set[str]:
    """Extract all element names from an RNG file.

    Args:
        rng_file: Path to the RNG file.

    Returns:
        Set of element tag names.
    """
    elements: set[str] = set()

    try:
        tree = ET.parse(rng_file)
        root = tree.getroot()

        # Find all <element> tags and extract names
        for elem in root.iter(f"{RNG_NS}element"):
            # Name can be in <name> child or 'name' attribute
            name_elem = elem.find(f"{RNG_NS}name")
            if name_elem is not None and name_elem.text:
                tag = name_elem.text.strip()
                if tag and tag != "*" and ":" not in tag:
                    elements.add(tag)
            elif "name" in elem.attrib:
                tag = elem.attrib["name"]
                if tag and tag != "*" and ":" not in tag:
                    elements.add(tag)

    except ET.ParseError as e:
        print(f"  WARNING: Failed to parse {rng_file.name}: {e}")

    return elements


def collect_elements_from_path(input_path: Path) -> set[str]:
    """Collect all element names from RNG file(s).

    Args:
        input_path: Path to RNG file or directory containing RNG files.

    Returns:
        Set of all element tag names found.
    """
    all_elements: set[str] = set()

    if input_path.is_file():
        print(f"Parsing {input_path}...")
        all_elements = extract_elements_from_rng(input_path)
    elif input_path.is_dir():
        rng_files = list(input_path.glob("*.rng"))
        print(f"Parsing {len(rng_files)} RNG files from {input_path}...")
        for rng_file in sorted(rng_files):
            elements = extract_elements_from_rng(rng_file)
            print(f"  {rng_file.name}: {len(elements)} elements")
            all_elements.update(elements)
    else:
        print(f"ERROR: Input not found: {input_path}")
        sys.exit(1)

    return all_elements


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert RNG schema to Bag schema using SchemaBuilder"
    )
    parser.add_argument(
        "input", type=Path, help="Input RNG file or directory containing RNG files"
    )
    parser.add_argument("output", type=Path, help="Output MessagePack file (.bag.mp)")
    parser.add_argument(
        "--void",
        type=str,
        default="",
        help="Comma-separated list of void element names",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON file for inspection",
    )

    args = parser.parse_args()

    from genro_bag import Bag
    from genro_bag.builders import SchemaBuilder

    void_elements = set(v.strip() for v in args.void.split(",") if v.strip())

    all_elements = collect_elements_from_path(args.input)
    print(f"\nTotal unique elements: {len(all_elements)}")

    if void_elements:
        actual_void = void_elements & all_elements
        print(f"Void elements: {len(actual_void)}")
    else:
        actual_void = set()

    print("\nBuilding schema with SchemaBuilder...")
    schema = Bag(builder=SchemaBuilder)

    for tag in sorted(all_elements):
        if tag in actual_void:
            schema.void(name=tag)
        else:
            schema.item(name=tag)

    node_count = len(list(schema))
    print(f"Total nodes: {node_count}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSerializing to {args.output}...")
    schema.builder.compile(args.output)

    size_kb = args.output.stat().st_size / 1024
    print(f"Output size: {size_kb:.1f} KB")

    if args.json:
        json_file = args.output.with_suffix(".json")
        json_data = schema.to_tytx(transport="json")
        json_file.write_text(json_data)
        print(f"JSON output: {json_file}")

    print("\nDone!")


if __name__ == "__main__":
    main()
