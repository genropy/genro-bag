# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Directory Resolver examples.

Demonstrates mapping filesystem directories to Bag:
- Basic directory scanning
- File filtering with include/exclude
- Lazy loading of file contents
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import DirectoryResolver


def create_test_directory() -> Path:
    """Create a temporary test directory structure."""
    tmpdir = Path(tempfile.mkdtemp())

    # Create structure
    (tmpdir / "config").mkdir()
    (tmpdir / "data").mkdir()

    # Create files
    (tmpdir / "readme.txt").write_text("This is the readme")
    (tmpdir / "config" / "settings.xml").write_text("<settings><debug>true</debug></settings>")
    (tmpdir / "config" / "database.json").write_text('{"host": "localhost", "port": 5432}')
    (tmpdir / "data" / "users.csv").write_text("id,name\n1,John\n2,Jane")
    (tmpdir / "data" / "products.csv").write_text("id,name,price\n1,Widget,10")

    return tmpdir


def demo_basic_directory():
    """Basic directory scanning."""
    print("=" * 60)
    print("Basic Directory Scanning")
    print("=" * 60)

    tmpdir = create_test_directory()

    # Create resolver
    resolver = DirectoryResolver(str(tmpdir))
    bag = Bag()
    bag.set_item("files", None, resolver=resolver)

    # Access triggers scan (use static=False to trigger resolver)
    files = bag.get_item("files", static=False)

    print(f"Directory: {tmpdir}")
    print("\nContents:")
    for path, node in files.walk():
        indent = "  " * path.count(".")
        is_dir = node.is_branch
        print(f"{indent}{node.label}{'/' if is_dir else ''}")

    # Cleanup
    import shutil

    shutil.rmtree(tmpdir)


def demo_filtered_directory():
    """Directory scanning with filters."""
    print("\n" + "=" * 60)
    print("Filtered Directory Scanning")
    print("=" * 60)

    tmpdir = create_test_directory()

    # Include only .xml and .json files
    resolver = DirectoryResolver(
        str(tmpdir),
        include="*.xml,*.json",
        ext="xml,json",
    )
    bag = Bag()
    bag.set_item("config_files", None, resolver=resolver)

    # Access triggers scan (use static=False to trigger resolver)
    files = bag.get_item("config_files", static=False)

    print(f"Directory: {tmpdir}")
    print("Filter: *.xml, *.json")
    print("\nMatching files:")
    for path, node in files.walk():
        indent = "  " * path.count(".")
        print(f"{indent}{node.label}")

    # Cleanup
    import shutil

    shutil.rmtree(tmpdir)


def demo():
    """Run all demos."""
    demo_basic_directory()
    demo_filtered_directory()


if __name__ == "__main__":
    demo()
