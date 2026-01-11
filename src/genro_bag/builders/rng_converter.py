# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RNG to Bag schema converter.

Converts RELAX NG (RNG) XML schema files to Bag schema format.
Extracts element definitions, content models, and void element detection.

Example:
    from genro_bag.builders import RngConverter

    converter = RngConverter('path/to/rng/files')
    converter.convert('output_schema.bag.mp')

    # Or get the schema Bag directly
    schema_bag = converter.to_bag()
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..bag import Bag

# RELAX NG namespace
RNG_NS = "{http://relaxng.org/ns/structure/1.0}"


class RngConverter:
    """Converts RNG schema files to Bag schema format.

    Parses RELAX NG XML files and extracts:
    - Element names
    - Void elements (those with <empty/> content)
    - Content model references (for future sub_tags resolution)

    Attributes:
        source: Path to RNG file or directory containing RNG files.
        elements: Dict mapping element name to its info dict.
        defines: Dict mapping define names to their content info.
    """

    def __init__(self, source: str | Path):
        """Initialize converter with RNG source.

        Args:
            source: Path to RNG file or directory containing RNG files.
        """
        self.source = Path(source)
        self.elements: dict[str, dict] = {}
        self.defines: dict[str, dict] = {}
        self._parsed = False

    def parse(self) -> RngConverter:
        """Parse RNG files and extract schema information.

        Returns:
            Self for method chaining.
        """
        if self._parsed:
            return self

        if self.source.is_file():
            self._parse_file(self.source)
        elif self.source.is_dir():
            for rng_file in sorted(self.source.glob("*.rng")):
                self._parse_file(rng_file)
        else:
            msg = f"RNG source not found: {self.source}"
            raise FileNotFoundError(msg)

        self._parsed = True
        return self

    def _parse_file(self, rng_file: Path) -> None:
        """Parse a single RNG file.

        Args:
            rng_file: Path to the RNG file.
        """
        try:
            tree = ET.parse(rng_file)
            root = tree.getroot()
        except ET.ParseError:
            return

        # First pass: collect all <define> blocks
        for define in root.iter(f"{RNG_NS}define"):
            name = define.get("name", "")
            if not name:
                continue

            info: dict = {"source": rng_file.name}

            # Check if this define contains <empty/>
            if define.find(f".//{RNG_NS}empty") is not None:
                info["empty"] = True

            # Collect <ref> references for content model
            refs = [ref.get("name", "") for ref in define.iter(f"{RNG_NS}ref")]
            if refs:
                info["refs"] = [r for r in refs if r]

            self.defines[name] = info

        # Second pass: extract elements
        for elem in root.iter(f"{RNG_NS}element"):
            tag = self._get_element_name(elem)
            if not tag or tag == "*" or ":" in tag:
                continue

            if tag in self.elements:
                continue

            info = {"source": rng_file.name}

            # Check if element has <empty/> directly
            if elem.find(f".//{RNG_NS}empty") is not None:
                info["void"] = True

            # Collect refs to check for void via defines
            refs = []
            for ref in elem.iter(f"{RNG_NS}ref"):
                ref_name = ref.get("name", "")
                if ref_name:
                    refs.append(ref_name)
                    # Check if referenced define is empty (void element)
                    if ref_name.endswith(".inner"):
                        define_info = self.defines.get(ref_name, {})
                        if define_info.get("empty"):
                            info["void"] = True

            if refs:
                info["refs"] = refs

            self.elements[tag] = info

    def _get_element_name(self, elem: ET.Element) -> str | None:
        """Extract element name from <element> tag.

        Args:
            elem: The <element> XML element.

        Returns:
            Element name or None if not found.
        """
        # Name can be in <name> child or 'name' attribute
        name_elem = elem.find(f"{RNG_NS}name")
        if name_elem is not None and name_elem.text:
            return name_elem.text.strip()
        return elem.get("name")

    def to_bag(self) -> Bag:
        """Convert parsed RNG to a Bag schema.

        Returns:
            Bag with SchemaBuilder containing all elements.
        """
        from ..bag import Bag
        from .schema_builder import SchemaBuilder

        self.parse()

        schema = Bag(builder=SchemaBuilder)

        for tag in sorted(self.elements):
            info = self.elements[tag]
            if info.get("void"):
                schema.item(tag, sub_tags="")
            else:
                schema.item(tag)

        return schema

    def convert(self, destination: str | Path, json_output: bool = False) -> Path:
        """Convert RNG to Bag schema and save to file.

        Args:
            destination: Output path for MessagePack file.
            json_output: Also output JSON file for inspection.

        Returns:
            Path to the output file.
        """
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)

        schema = self.to_bag()
        schema.builder.compile(dest)

        if json_output:
            json_file = dest.with_suffix(".json")
            json_data = schema.to_tytx(transport="json")
            json_file.write_text(json_data)

        return dest

    def get_void_elements(self) -> set[str]:
        """Get set of void element names.

        Returns:
            Set of element names that are void (no children allowed).
        """
        self.parse()
        return {tag for tag, info in self.elements.items() if info.get("void")}

    def __len__(self) -> int:
        """Return number of elements found."""
        self.parse()
        return len(self.elements)

    def __contains__(self, tag: str) -> bool:
        """Check if element exists in schema."""
        self.parse()
        return tag in self.elements

    def __iter__(self):
        """Iterate over element names."""
        self.parse()
        return iter(sorted(self.elements))
