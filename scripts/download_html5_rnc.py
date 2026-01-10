#!/usr/bin/env python3
# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Download RNC schema files and convert to RNG.

Can download from any URL or use the default HTML5 schema from validator.nu.

Usage:
    # Download HTML5 schema (default)
    python scripts/download_html5_rnc.py

    # Download from custom URL
    python scripts/download_html5_rnc.py --url https://example.com/schema.rnc

    # Specify output directory
    python scripts/download_html5_rnc.py --output /path/to/output

Requirements:
    pip install rnc2rng
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# Default HTML5 RNC files from validator.nu
HTML5_RNC_FILES = [
    "applications.rnc",
    "aria.rnc",
    "block.rnc",
    "common.rnc",
    "core-scripting.rnc",
    "data.rnc",
    "embed.rnc",
    "form-datatypes.rnc",
    "html5.rnc",
    "html5exclusions.rnc",
    "media.rnc",
    "meta.rnc",
    "microdata.rnc",
    "phrase.rnc",
    "rdfa.rnc",
    "revision.rnc",
    "ruby.rnc",
    "sectional.rnc",
    "structural.rnc",
    "tables.rnc",
    "web-components.rnc",
    "web-forms-scripting.rnc",
    "web-forms.rnc",
    "web-forms2-scripting.rnc",
    "web-forms2.rnc",
    "xhtml5.rnc",
]

HTML5_BASE_URL = "https://raw.githubusercontent.com/validator/validator/main/schema/html5"


def download_rnc_file(url: str, dest: Path) -> bool:
    """Download a single RNC file from URL.

    Args:
        url: URL to download from.
        dest: Destination path.

    Returns:
        True if successful, False otherwise.
    """
    if dest.exists():
        print(f"  {dest.name} (cached)")
        return True

    print(f"  {dest.name}...")
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read()
        dest.write_bytes(content)
        return True
    except Exception as e:
        print(f"    ERROR: {e}")
        return False


def convert_rnc_to_rng(rnc_file: Path) -> Path | None:
    """Convert a single RNC file to RNG format.

    Args:
        rnc_file: Path to the RNC file.

    Returns:
        Path to the RNG file, or None if conversion failed.
    """
    try:
        from rnc2rng import parser, serializer
    except ImportError:
        print("ERROR: rnc2rng not installed. Run: pip install rnc2rng")
        sys.exit(1)

    rng_file = rnc_file.with_suffix(".rng")

    if rng_file.exists():
        print(f"  {rng_file.name} (cached)")
        return rng_file

    print(f"  {rnc_file.name} -> {rng_file.name}...")
    try:
        ast = parser.parse(f=str(rnc_file))
        rng_content = serializer.XMLSerializer().toxml(ast)
        rng_file.write_text(rng_content)
        return rng_file
    except Exception as e:
        print(f"    ERROR: {e}")
        return None


def download_html5_schema(output_dir: Path) -> list[Path]:
    """Download all HTML5 RNC files from validator.nu repository.

    Args:
        output_dir: Directory to save files.

    Returns:
        List of downloaded RNC file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(HTML5_RNC_FILES)} RNC files from validator.nu...")
    print(f"Output directory: {output_dir}")

    downloaded = []
    for filename in HTML5_RNC_FILES:
        url = f"{HTML5_BASE_URL}/{filename}"
        dest = output_dir / filename
        if download_rnc_file(url, dest):
            downloaded.append(dest)

    print(f"Download complete: {len(downloaded)}/{len(HTML5_RNC_FILES)} files")
    return downloaded


def download_from_url(url: str, output_dir: Path) -> Path | None:
    """Download a single RNC file from any URL.

    Args:
        url: URL to download from.
        output_dir: Directory to save file.

    Returns:
        Path to downloaded file, or None if failed.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract filename from URL
    parsed = urlparse(url)
    filename = Path(parsed.path).name
    if not filename.endswith(".rnc"):
        filename = f"{filename}.rnc"

    dest = output_dir / filename
    print(f"Downloading from {url}...")
    print(f"Output directory: {output_dir}")

    if download_rnc_file(url, dest):
        return dest
    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download RNC schema files and convert to RNG"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="URL of RNC file to download (default: HTML5 schema from validator.nu)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (default: src/genro_bag/builders/schemas/html5)",
    )
    parser.add_argument(
        "--no-convert",
        action="store_true",
        help="Skip RNC to RNG conversion",
    )

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    if args.output:
        output_dir = args.output
    else:
        output_dir = project_root / "src/genro_bag/builders/schemas/html5"

    if args.url:
        # Download single file from URL
        rnc_file = download_from_url(args.url, output_dir)
        if rnc_file and not args.no_convert:
            print("\nConverting to RNG...")
            convert_rnc_to_rng(rnc_file)
    else:
        # Download HTML5 schema (default)
        rnc_files = download_html5_schema(output_dir)
        if rnc_files and not args.no_convert:
            print("\nConverting to RNG...")
            for rnc_file in rnc_files:
                convert_rnc_to_rng(rnc_file)

    print("\nDone!")


if __name__ == "__main__":
    main()
