#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Convert RELAX NG (RNG/RNC) schemas to BagBuilder schema format.

This script converts RELAX NG schema files to a .bag.mp schema file that can
be used with BagBuilderBase via schema_path.

Features:
- Download RNC files from GitHub URL
- Convert RNC to RNG (requires rnc2rng)
- Parse RNG and extract elements, sub_tags, content models
- Generate schema with @flow, @phrasing, @metadata abstracts
- Save as .bag.mp or .bag.json

Usage:
    # From local RNG directory
    python rng_to_schema.py path/to/rng/ -o schema.bag.mp

    # From local RNC directory (auto-converts to RNG)
    python rng_to_schema.py path/to/rnc/ -o schema.bag.mp

    # From GitHub URL (downloads and converts)
    python rng_to_schema.py --url https://github.com/validator/validator/tree/main/schema/html5 -o schema.bag.mp

    # With JSON output for inspection
    python rng_to_schema.py path/to/rng/ -o schema.bag.mp --json

Example for HTML5:
    python rng_to_schema.py temp/html5_rng/ -o schemas/html5_schema.bag.mp
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from genro_bag import Bag
from genro_bag.builders import SchemaBuilder


def download_from_github(url: str, dest_dir: Path) -> list[str]:
    """Download RNC/RNG files from GitHub directory URL.

    Args:
        url: GitHub URL to directory (e.g., https://github.com/user/repo/tree/branch/path)
        dest_dir: Local directory to save files

    Returns:
        List of downloaded file paths
    """
    import re

    # Parse GitHub URL
    # Format: https://github.com/owner/repo/tree/branch/path
    match = re.match(r'https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)', url)
    if not match:
        raise ValueError(f"Invalid GitHub URL format: {url}")

    owner, repo, branch, path = match.groups()

    # Get directory listing via GitHub API
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"

    print(f"Fetching file list from GitHub API...")

    with urllib.request.urlopen(api_url) as response:
        files = json.loads(response.read().decode())

    downloaded = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    for file_info in files:
        name = file_info['name']
        if name.endswith('.rnc') or name.endswith('.rng'):
            raw_url = file_info['download_url']
            dest_path = dest_dir / name

            print(f"  Downloading {name}...")
            urllib.request.urlretrieve(raw_url, dest_path)
            downloaded.append(str(dest_path))

    print(f"Downloaded {len(downloaded)} files")
    return downloaded


def convert_rnc_to_rng(rnc_dir: Path, rng_dir: Path) -> list[str]:
    """Convert all RNC files in directory to RNG using rnc2rng.

    Args:
        rnc_dir: Directory containing .rnc files
        rng_dir: Directory to write .rng files

    Returns:
        List of converted .rng file paths
    """
    try:
        subprocess.run(['rnc2rng', '--help'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise RuntimeError("rnc2rng not found. Install with: pip install rnc2rng")

    rng_dir.mkdir(parents=True, exist_ok=True)
    converted = []
    failed = []

    for rnc_file in sorted(rnc_dir.glob('*.rnc')):
        rng_file = rng_dir / rnc_file.with_suffix('.rng').name

        result = subprocess.run(
            ['rnc2rng', str(rnc_file), str(rng_file)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            converted.append(str(rng_file))
            print(f"  Converted {rnc_file.name}")
        else:
            failed.append(rnc_file.name)
            print(f"  FAILED: {rnc_file.name}")

    print(f"Converted {len(converted)} files, {len(failed)} failed")
    return converted


def load_rng_files(rng_dir: Path) -> Bag:
    """Load all RNG files and merge into single Bag with tag_attribute='name'.

    Args:
        rng_dir: Directory containing .rng files

    Returns:
        Merged Bag with all defines
    """
    all_defines = Bag()

    for rng_file in sorted(rng_dir.glob('*.rng')):
        with open(rng_file, encoding='utf-8') as f:
            xml = f.read()

        bag = Bag.from_xml(xml, tag_attribute='name')
        grammar = bag.get('grammar')

        if grammar:
            for node in grammar:
                # Merge into all_defines
                all_defines.set_item(node.label, node.value, **dict(node.attr))

    return all_defines




def get_element_name(elem_bag: Bag) -> str | None:
    """Extract HTML element name from .elem definition."""
    try:
        element = elem_bag.get('element')
        if element:
            name_node = element.get_node('name')
            if name_node:
                return name_node.value
    except Exception:
        pass
    return None


def get_content_model_from_inner(inner_bag: Bag) -> str | None:
    """Determine content model from inner definition by searching for references.

    Looks for patterns like 'common.inner.flow' or 'common.inner.phrasing'
    in the inner definition structure.

    Returns:
        Content model name ('flow', 'phrasing', 'metadata') or None.
    """
    if not isinstance(inner_bag, Bag):
        return None

    inner_str = str(inner_bag).lower()
    # Check in priority order (flow is most common)
    if 'flow' in inner_str:
        return 'flow'
    if 'phrasing' in inner_str:
        return 'phrasing'
    if 'metadata' in inner_str:
        return 'metadata'
    return None


def get_direct_refs(inner_bag: Bag) -> list[str]:
    """Extract direct element references from inner definition.

    Looks for references to other elements (not content models) that are
    explicitly allowed as children.

    Returns:
        List of element names that are direct children.
    """
    if not isinstance(inner_bag, Bag):
        return []

    direct_refs: list[str] = []

    def walk(bag: Bag) -> None:
        if not isinstance(bag, Bag):
            return
        for node in bag:
            # Skip common.* references (content models)
            if node.label == 'common':
                continue
            if isinstance(node.value, Bag):
                # Check if this is a reference to an element
                for child in node.value:
                    if child.label == 'elem' and (child.value == '' or child.value is None):
                        direct_refs.append(node.label)
                        break
                walk(node.value)

    walk(inner_bag)
    return direct_refs


def build_schema(all_defines: Bag) -> Bag:
    """Build schema Bag using SchemaBuilder.

    Determines content model for each element by examining its inner definition.

    Args:
        all_defines: Merged Bag with all defines

    Returns:
        Schema Bag ready for serialization
    """
    schema = Bag(builder=SchemaBuilder)

    # Track elements by content model for abstracts
    content_models: dict[str, list[str]] = {
        'flow': [],
        'phrasing': [],
        'metadata': [],
    }

    elements_defined: set[str] = set()

    for node in all_defines:
        elem_bag = node.value
        if not isinstance(elem_bag, Bag):
            continue

        elem_def = elem_bag.get('elem')
        if not elem_def:
            continue

        html_name = get_element_name(elem_def)
        if not html_name or html_name in elements_defined:
            continue

        elements_defined.add(html_name)

        # Determine content model from inner
        inner_def = elem_bag.get('inner')
        cm = get_content_model_from_inner(inner_def)
        direct_refs = get_direct_refs(inner_def)

        # Track which elements belong to each content model
        if cm:
            content_models[cm].append(html_name)

        # Create schema item
        inherits_from = f'@{cm}' if cm else None

        if direct_refs and inherits_from:
            schema.item(html_name, sub_tags=','.join(direct_refs), inherits_from=inherits_from)
        elif inherits_from:
            schema.item(html_name, inherits_from=inherits_from)
        elif direct_refs:
            schema.item(html_name, sub_tags=','.join(direct_refs))
        else:
            # Void element (no children)
            schema.item(html_name, sub_tags='')

    # Define abstract content models with their member elements
    for cm_name, elements in content_models.items():
        if elements:
            schema.item(f'@{cm_name}', sub_tags=','.join(sorted(set(elements))))

    return schema


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Convert RELAX NG schemas to BagBuilder schema format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        'input',
        nargs='?',
        type=Path,
        help='Input directory containing RNG or RNC files'
    )
    parser.add_argument(
        '--url',
        help='GitHub URL to download RNC/RNG files from'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        type=Path,
        help='Output schema file (.bag.mp or .bag.json)'
    )
    parser.add_argument(
        '--format',
        choices=['auto', 'rng', 'rnc'],
        default='auto',
        help='Input format (default: auto-detect from extension)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Also output JSON file for inspection'
    )
    parser.add_argument(
        '--keep-temp',
        action='store_true',
        help='Keep temporary files (for debugging)'
    )

    args = parser.parse_args()

    if not args.input and not args.url:
        parser.error("Either input directory or --url is required")

    # Determine working directories
    temp_dir = None
    rng_dir: Path

    if args.url:
        # Download from URL
        temp_dir = Path(tempfile.mkdtemp(prefix='rng_schema_'))
        rnc_dir = temp_dir / 'rnc'
        rng_dir = temp_dir / 'rng'

        print(f"Downloading from {args.url}...")
        download_from_github(args.url, rnc_dir)

        # Check if we got RNC or RNG
        has_rnc = any(rnc_dir.glob('*.rnc'))
        has_rng = any(rnc_dir.glob('*.rng'))

        if has_rnc:
            print("\nConverting RNC to RNG...")
            convert_rnc_to_rng(rnc_dir, rng_dir)
        elif has_rng:
            rng_dir = rnc_dir
        else:
            print("ERROR: No RNC or RNG files found")
            sys.exit(1)
    else:
        input_dir = args.input

        if not input_dir.exists():
            print(f"ERROR: Input directory not found: {input_dir}")
            sys.exit(1)

        # Auto-detect format
        has_rnc = any(input_dir.glob('*.rnc'))
        has_rng = any(input_dir.glob('*.rng'))

        if args.format == 'rnc' or (args.format == 'auto' and has_rnc and not has_rng):
            # Convert RNC to RNG
            temp_dir = Path(tempfile.mkdtemp(prefix='rng_schema_'))
            rng_dir = temp_dir / 'rng'

            print("Converting RNC to RNG...")
            convert_rnc_to_rng(input_dir, rng_dir)
        elif has_rng:
            rng_dir = input_dir
        else:
            print("ERROR: No RNG files found in input directory")
            sys.exit(1)

    # Load RNG files
    print(f"\nLoading RNG files from {rng_dir}...")
    all_defines = load_rng_files(rng_dir)
    print(f"  Loaded {len(all_defines)} top-level defines")

    # Build schema (content models are extracted during build)
    print("\nBuilding schema...")
    schema = build_schema(all_defines)

    # Count elements
    n_abstracts = sum(1 for n in schema if n.label.startswith('@'))
    n_elements = len(schema) - n_abstracts
    print(f"  {n_abstracts} abstracts, {n_elements} elements")

    # Save output
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.suffix == '.mp' or str(args.output).endswith('.bag.mp'):
        data = schema.to_tytx(transport='msgpack')
        args.output.write_bytes(data)
        print(f"\nSaved to {args.output} ({len(data)} bytes)")
    else:
        data = schema.to_tytx(transport='json')
        args.output.write_text(data)
        print(f"\nSaved to {args.output} ({len(data)} bytes)")

    # Optional JSON output
    if args.json:
        json_path = args.output.with_suffix('.json')
        json_data = schema.to_tytx(transport='json')
        json_path.write_text(json_data)
        print(f"JSON output: {json_path}")

    # Cleanup
    if temp_dir and not args.keep_temp:
        shutil.rmtree(temp_dir)
        print("Cleaned up temporary files")
    elif temp_dir:
        print(f"Temporary files kept at {temp_dir}")

    print("\nDone!")


if __name__ == '__main__':
    main()
