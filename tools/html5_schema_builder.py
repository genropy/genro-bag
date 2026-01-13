#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Generate HTML5 schema for HtmlBuilder from W3C Validator RNG files.

IMPORTANT: This script is specific to HTML5 W3C Validator schema format.
It will NOT work with arbitrary RELAX NG files because it relies on the
specific structure used by validator.nu (e.g., 'section.elem', 'section.inner',
'common.inner.flow', etc.).

What this script does:
1. Parses RNG files from W3C HTML5 Validator (supports recursive download)
2. Collects all HTML element names from <element><name>X</name> patterns
3. Builds a global index of all <define> elements (handles combine=choice|group|interleave)
4. Uses RELAX NG semantics (first_elements, nullable) to compute allowed children
5. Generates a schema with sub_tags for each element
6. Saves as .bag.mp for use with HtmlBuilder

Prerequisites:
    pip install rnc2rng lxml  # rnc2rng only if using RNC format

Usage:
    # From local RNG directory (e.g., downloaded from validator.nu)
    python -m genro_bag.builders.html.html5_schema_builder path/to/rng/ -o html5_schema.bag.mp

    # From local RNC directory (auto-converts to RNG)
    python -m genro_bag.builders.html.html5_schema_builder path/to/rnc/ -o html5_schema.bag.mp

    # Download directly from GitHub (recursive)
    python -m genro_bag.builders.html.html5_schema_builder \\
        --url https://github.com/validator/validator/tree/main/schema/html5 \\
        -o html5_schema.bag.mp

    # With JSON output and verbose diagnostics
    python -m genro_bag.builders.html.html5_schema_builder path/to/rng/ -o html5_schema.bag.mp --json -v

To regenerate the bundled HTML5 schema (run from project root):
    python -m genro_bag.builders.html.html5_schema_builder \\
        --url https://github.com/nickhutchinson/html5-validator/tree/master/schema \\
        -o src/genro_bag/builders/html/html5_schema.bag.mp

Output format:
    The schema contains elements with sub_tags listing allowed children:
    - div (sub_tags='a,abbr,address,...')  # flow content children
    - ul (sub_tags='li')  # specific children
    - br (sub_tags='')  # void element, no children
"""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

from lxml import etree

from genro_bag import Bag
from genro_bag.builders import SchemaBuilder


def download_from_github(url: str, dest_dir: Path) -> list[str]:
    """Download RNC/RNG files from GitHub directory URL (recursive).

    Args:
        url: GitHub URL to directory (e.g., https://github.com/user/repo/tree/branch/path)
        dest_dir: Local directory to save files

    Returns:
        List of downloaded file paths
    """
    import re

    # Parse GitHub URL
    # Format: https://github.com/owner/repo/tree/branch/path
    match = re.match(r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.+)", url)
    if not match:
        raise ValueError(f"Invalid GitHub URL format: {url}")

    owner, repo, branch, path = match.groups()

    downloaded: list[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)

    def fetch_directory(dir_path: str, local_dir: Path) -> None:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{dir_path}?ref={branch}"
        print(f"Fetching {dir_path}...")

        req = urllib.request.Request(api_url, headers={"User-Agent": "html5-schema-builder"})
        with urllib.request.urlopen(req) as response:
            items = json.loads(response.read().decode())

        local_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            name = item["name"]
            item_type = item["type"]

            if item_type == "dir":
                # Recurse into subdirectory
                fetch_directory(item["path"], local_dir / name)
            elif item_type == "file" and (name.endswith(".rnc") or name.endswith(".rng")):
                raw_url = item["download_url"]
                dest_path = local_dir / name
                print(f"  Downloading {name}...")
                urllib.request.urlretrieve(raw_url, dest_path)
                downloaded.append(str(dest_path))

    fetch_directory(path, dest_dir)
    print(f"Downloaded {len(downloaded)} files")
    return downloaded


def convert_rnc_to_rng(rnc_dir: Path, rng_dir: Path) -> list[str]:
    """Convert all RNC files in directory (recursively) to RNG using rnc2rng.

    Args:
        rnc_dir: Directory containing .rnc files (searched recursively)
        rng_dir: Directory to write .rng files (preserves relative structure)

    Returns:
        List of converted .rng file paths
    """
    try:
        subprocess.run(["rnc2rng", "--help"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        raise RuntimeError("rnc2rng not found. Install with: pip install rnc2rng") from err

    rng_dir.mkdir(parents=True, exist_ok=True)
    converted = []
    failed = []

    for rnc_file in sorted(rnc_dir.rglob("*.rnc")):
        # Preserve relative directory structure
        rel = rnc_file.relative_to(rnc_dir)
        rng_file = (rng_dir / rel).with_suffix(".rng")
        rng_file.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["rnc2rng", str(rnc_file), str(rng_file)], capture_output=True, text=True
        )

        if result.returncode == 0:
            converted.append(str(rng_file))
            print(f"  Converted {rel}")
        else:
            failed.append(str(rel))
            print(f"  FAILED: {rel}")

    print(f"Converted {len(converted)} files, {len(failed)} failed")
    return converted


# =============================================================================
# RELAX NG Semantic Parser
# =============================================================================

RNG_NS = "http://relaxng.org/ns/structure/1.0"
NS = {"rng": RNG_NS}


COMBINE_WRAPPER = {
    "choice": "choice",
    "interleave": "interleave",
    "group": "group",
}


def build_defs(rng_dir: Path) -> dict[str, etree._Element]:
    """Index all <define> elements by name across all RNG files.

    Handles combine="choice|interleave|group" by creating a synthetic wrapper
    element containing all patterns from multiple define elements with the same name.
    Also includes the base definition (without combine) if one exists.

    If the same name is seen with different combine types, we fall back to "choice"
    (conservative) and print a warning.
    """
    parser = etree.XMLParser(recover=True, huge_tree=True)

    base_defs: dict[str, etree._Element] = {}  # defines without combine
    combined_type: dict[str, str] = {}  # name -> combine type
    combined_patterns: dict[str, list[etree._Element]] = {}  # name -> list of pattern children

    for f in sorted(rng_dir.rglob("*.rng")):
        tree = etree.parse(str(f), parser)
        for d in tree.xpath("//rng:define", namespaces=NS):
            name = d.get("name")
            if not name:
                continue

            combine = d.get("combine")
            if combine in COMBINE_WRAPPER:
                prev = combined_type.get(name)
                if prev is None:
                    combined_type[name] = combine
                elif prev != combine:
                    # Conservative fallback: choice
                    combined_type[name] = "choice"
                    print(
                        f"WARNING: define '{name}' has mixed combine types "
                        f"({prev!r} vs {combine!r}); falling back to 'choice'."
                    )

                lst = combined_patterns.setdefault(name, [])
                for ch in d:
                    if isinstance(ch.tag, str) and ch.tag.startswith(f"{{{RNG_NS}}}"):
                        lst.append(ch)
            else:
                # Base definition (no combine attribute)
                if name in base_defs:
                    print(
                        f"WARNING: duplicate base <define name='{name}'> without combine; last one wins."
                    )
                base_defs[name] = d

    defs: dict[str, etree._Element] = {}

    # Build combined defs with synthetic wrapper
    for name, patterns in combined_patterns.items():
        if not patterns:
            continue

        combine_t = combined_type.get(name, "choice")
        wrapper_tag = COMBINE_WRAPPER.get(combine_t, "choice")
        wrapper_elem = etree.Element(f"{{{RNG_NS}}}{wrapper_tag}")

        # Include base definition first if present
        base = base_defs.get(name)
        if base is not None:
            for ch in base:
                if isinstance(ch.tag, str) and ch.tag.startswith(f"{{{RNG_NS}}}"):
                    wrapper_elem.append(copy.deepcopy(ch))

        # Add all combined patterns
        for p in patterns:
            wrapper_elem.append(copy.deepcopy(p))

        define_wrapper = etree.Element(f"{{{RNG_NS}}}define")
        define_wrapper.set("name", name)
        define_wrapper.append(wrapper_elem)
        defs[name] = define_wrapper

    # Add base defs not overridden by combined ones
    for name, d in base_defs.items():
        if name not in defs:
            defs[name] = d

    return defs


def collect_all_element_names(rng_dir: Path) -> set[str]:
    """Collect all HTML element names from <element><name>X</name> patterns."""
    parser = etree.XMLParser(recover=True, huge_tree=True)
    names: set[str] = set()

    for f in sorted(rng_dir.rglob("*.rng")):
        tree = etree.parse(str(f), parser)
        for n in tree.xpath("//rng:element/rng:name/text()", namespaces=NS):
            if n:
                names.add(n.strip())
    return names


def _first_child_pattern(node: etree._Element) -> etree._Element | None:
    """Get the first RNG pattern child of a node."""
    for ch in node:
        if isinstance(ch.tag, str) and ch.tag.startswith(f"{{{RNG_NS}}}"):
            return ch
    return None


def resolve_ref(defs: dict[str, etree._Element], name: str) -> etree._Element | None:
    """Resolve a ref to its define's pattern."""
    d = defs.get(name)
    if d is None:
        return None
    return _first_child_pattern(d)


def nullable(
    defs: dict[str, etree._Element], p: etree._Element, memo: dict[str, bool], stack: set[str]
) -> bool:
    """Check if a pattern can match empty content.

    The memo uses define names as keys (not element IDs) to avoid issues
    with copied elements having reused Python object IDs.
    """
    if p is None:
        return True

    tag = etree.QName(p).localname

    if tag in ("empty",):
        return True
    if tag in ("text", "value", "data", "element", "attribute"):
        return False

    if tag == "optional" or tag == "zeroOrMore":
        return True

    if tag == "oneOrMore":
        child = _first_child_pattern(p)
        return nullable(defs, child, memo, stack) if child is not None else True

    if tag == "choice":
        for ch in p:
            if not isinstance(ch.tag, str):
                continue
            if nullable(defs, ch, memo, stack):
                return True
        return False

    if tag in ("group", "interleave"):
        for ch in p:
            if not isinstance(ch.tag, str):
                continue
            if not nullable(defs, ch, memo, stack):
                return False
        return True

    if tag == "ref":
        name = p.get("name", "")
        if not name or name in stack:
            return False
        # Use define name for memoization
        if name in memo:
            return memo[name]
        stack.add(name)
        tgt = resolve_ref(defs, name)
        res = nullable(defs, tgt, memo, stack) if tgt is not None else False
        stack.remove(name)
        memo[name] = res
        return res

    return False


def first_elements(
    defs: dict[str, etree._Element],
    p: etree._Element,
    memo: dict[str, set[str]],
    stack: set[str],
    nullable_memo: dict[str, bool],
) -> set[str]:
    """Compute which elements can appear as first child (RELAX NG semantics).

    The memo uses define names as keys (not element IDs) to avoid issues
    with copied elements having reused Python object IDs.
    """
    if p is None:
        return set()

    tag = etree.QName(p).localname

    if tag == "element":
        n = p.find("rng:name", namespaces=NS)
        if n is not None and n.text:
            return {n.text.strip()}
        return set()

    if tag in ("empty", "text", "value", "data", "attribute"):
        return set()

    if tag in ("optional", "zeroOrMore", "oneOrMore"):
        child = _first_child_pattern(p)
        return (
            first_elements(defs, child, memo, stack, nullable_memo) if child is not None else set()
        )

    if tag in ("choice", "interleave"):
        res: set[str] = set()
        for ch in p:
            if isinstance(ch.tag, str):
                res |= first_elements(defs, ch, memo, stack, nullable_memo)
        return res

    if tag == "group":
        children = [ch for ch in p if isinstance(ch.tag, str)]
        if not children:
            return set()

        # Correct group semantics: first(A) + first(B) only if A is nullable
        # Stop adding when we hit a non-nullable element
        res: set[str] = set()
        all_prev_nullable = True

        for part in children:
            if not all_prev_nullable:
                break
            res |= first_elements(defs, part, memo, stack, nullable_memo)
            all_prev_nullable = nullable(defs, part, nullable_memo, set())

        return res

    if tag == "ref":
        name = p.get("name", "")
        if not name or name in stack:
            return set()
        # Use define name for memoization
        if name in memo:
            return memo[name]
        stack.add(name)
        tgt = resolve_ref(defs, name)
        res = first_elements(defs, tgt, memo, stack, nullable_memo) if tgt is not None else set()
        stack.remove(name)
        memo[name] = res
        return res

    return set()


def build_schema(rng_dir: Path, verbose: bool = False) -> Bag:
    """Build schema Bag from RNG files using RELAX NG semantic analysis.

    Args:
        rng_dir: Directory containing .rng files
        verbose: If True, print diagnostic info for elements without .inner

    Returns:
        Schema Bag ready for serialization
    """
    schema = Bag(builder=SchemaBuilder)

    defs = build_defs(rng_dir)
    elements = collect_all_element_names(rng_dir)
    print(f"  Found {len(elements)} elements, {len(defs)} defines")

    fe_memo: dict[str, set[str]] = {}
    nullable_memo: dict[str, bool] = {}
    void_elements: list[str] = []

    for e in sorted(elements):
        inner = resolve_ref(defs, f"{e}.inner")

        # sub_tags: if no .inner => void element
        if inner is None:
            sub_tags = ""
            void_elements.append(e)
        else:
            kids = first_elements(defs, inner, fe_memo, set(), nullable_memo)
            sub_tags = ",".join(sorted(kids))

        schema.item(e, sub_tags=sub_tags)

    if verbose and void_elements:
        print(f"  Elements without .inner (void/empty): {', '.join(void_elements)}")

    return schema


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert RELAX NG schemas to BagBuilder schema format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "input", nargs="?", type=Path, help="Input directory containing RNG or RNC files"
    )
    parser.add_argument("--url", help="GitHub URL to download RNC/RNG files from")
    parser.add_argument(
        "-o", "--output", required=True, type=Path, help="Output schema file (.bag.mp or .bag.json)"
    )
    parser.add_argument(
        "--format",
        choices=["auto", "rng", "rnc"],
        default="auto",
        help="Input format (default: auto-detect from extension)",
    )
    parser.add_argument("--json", action="store_true", help="Also output JSON file for inspection")
    parser.add_argument(
        "--keep-temp", action="store_true", help="Keep temporary files (for debugging)"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print diagnostic info (e.g., elements without .inner)",
    )

    args = parser.parse_args()

    if not args.input and not args.url:
        parser.error("Either input directory or --url is required")

    # Determine working directories
    temp_dir = None
    rng_dir: Path

    if args.url:
        # Download from URL
        temp_dir = Path(tempfile.mkdtemp(prefix="rng_schema_"))
        rnc_dir = temp_dir / "rnc"
        rng_dir = temp_dir / "rng"

        print(f"Downloading from {args.url}...")
        download_from_github(args.url, rnc_dir)

        # Check if we got RNC or RNG (recursive)
        has_rnc = any(rnc_dir.rglob("*.rnc"))
        has_rng = any(rnc_dir.rglob("*.rng"))

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

        # Auto-detect format (recursive)
        has_rnc = any(input_dir.rglob("*.rnc"))
        has_rng = any(input_dir.rglob("*.rng"))

        if args.format == "rnc" or (args.format == "auto" and has_rnc and not has_rng):
            # Convert RNC to RNG
            temp_dir = Path(tempfile.mkdtemp(prefix="rng_schema_"))
            rng_dir = temp_dir / "rng"

            print("Converting RNC to RNG...")
            convert_rnc_to_rng(input_dir, rng_dir)
        elif has_rng:
            rng_dir = input_dir
        else:
            print("ERROR: No RNG files found in input directory")
            sys.exit(1)

    # Build schema using RELAX NG semantic analysis
    print(f"\nBuilding schema from {rng_dir}...")
    schema = build_schema(rng_dir, verbose=args.verbose)

    # Count elements
    n_abstracts = sum(1 for n in schema if n.label.startswith("@"))
    n_elements = len(schema) - n_abstracts
    print(f"  {n_abstracts} abstracts, {n_elements} elements")

    # Save output
    args.output.parent.mkdir(parents=True, exist_ok=True)

    if args.output.suffix == ".mp" or str(args.output).endswith(".bag.mp"):
        data = schema.to_tytx(transport="msgpack")
        args.output.write_bytes(data)
        print(f"\nSaved to {args.output} ({len(data)} bytes)")
    else:
        data = schema.to_tytx(transport="json")
        args.output.write_text(data)
        print(f"\nSaved to {args.output} ({len(data)} bytes)")

    # Optional JSON output
    if args.json:
        json_path = args.output.with_suffix(".json")
        json_data = schema.to_tytx(transport="json")
        json_path.write_text(json_data)
        print(f"JSON output: {json_path}")

    # Cleanup
    if temp_dir and not args.keep_temp:
        shutil.rmtree(temp_dir)
        print("Cleaned up temporary files")
    elif temp_dir:
        print(f"Temporary files kept at {temp_dir}")

    print("\nDone!")


if __name__ == "__main__":
    main()
