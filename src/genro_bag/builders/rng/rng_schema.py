# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""RngBuilder - Dynamic builder generated from RNG schema.

Creates a builder class dynamically by parsing RELAX NG (RNG) schema files.
The resulting builder populates _schema (a Bag) used by BagBuilderBase.

Schema structure::

    _schema = Bag()  # flat structure, one node per element
    # node.label = element name
    # node.attr = {sub_tags, void, ...}

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders.rng import RngBuilder
    >>>
    >>> bag = Bag(builder=RngBuilder, builder_rng_source='html5/')
    >>> doc = bag.html()
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from genro_bag.builder import BagBuilderBase

if TYPE_CHECKING:
    from genro_bag import Bag, BagNode


class RngBuilder(BagBuilderBase):
    """Builder dynamically generated from RNG schema.

    Parses RNG files and populates _schema for BagBuilderBase validation.
    Supports single file or directory of RNG files.
    """

    def __init__(self, bag: Bag, rng_source: str | Path):
        """Initialize builder from RNG file or directory.

        Args:
            bag: The Bag instance this builder is attached to.
            rng_source: Path to RNG file or directory containing RNG files.
        """
        from genro_bag import Bag as BagClass

        super().__init__(bag)

        self._source = Path(rng_source)
        self._defines: dict[str, dict[str, Any]] = {}
        self._schema: Bag = BagClass()

        self._build_schema()

    def _build_schema(self) -> None:
        """Parse RNG files and build schema."""
        if self._source.is_file():
            self._parse_rng_file(self._source)
        elif self._source.is_dir():
            for rng_file in sorted(self._source.glob("*.rng")):
                self._parse_rng_file(rng_file)

    def _parse_rng_file(self, rng_file: Path) -> None:
        """Parse a single RNG file using Bag.from_xml().

        Args:
            rng_file: Path to the RNG file.
        """
        from genro_bag import Bag as BagClass

        try:
            rng_content = rng_file.read_text()
            rng_bag = BagClass.from_xml(rng_content)
        except Exception:
            return

        # Find the grammar root
        grammar_node = self._find_grammar(rng_bag)
        if grammar_node is None:
            return

        # First pass: collect all <define> blocks
        self._collect_defines(grammar_node)

        # Second pass: extract elements
        self._collect_elements(grammar_node)

    def _find_grammar(self, rng_bag: Bag) -> BagNode | None:
        """Find the rng:grammar root node.

        Args:
            rng_bag: Bag loaded from RNG XML.

        Returns:
            The grammar BagNode or None.
        """
        for node in rng_bag:
            base = self._get_base_tag(node.label)
            if base == "grammar":
                return node
        return None

    def _get_base_tag(self, label: str) -> str:
        """Extract base tag from label.

        'rng:define_1' -> 'define'
        'element_0' -> 'element'

        Args:
            label: The node label.

        Returns:
            Base tag name without namespace or suffix.
        """
        # Remove namespace prefix
        if ":" in label:
            label = label.split(":")[-1]
        # Remove numeric suffix
        if "_" in label:
            label = label.rsplit("_", 1)[0]
        return label

    def _collect_defines(self, grammar_node: BagNode) -> None:
        """Collect all <define> blocks into self._defines.

        Args:
            grammar_node: The grammar root node.
        """
        if not grammar_node.is_branch:
            return

        for node in grammar_node.value:
            base = self._get_base_tag(node.label)
            if base != "define":
                continue

            name = node.attr.get("name", "")
            if not name:
                continue

            info: dict[str, Any] = {}

            # Check if this define contains <empty/> (void element)
            if self._has_empty(node):
                info["empty"] = True

            # Collect <ref> names for content model resolution
            refs = self._collect_refs(node)
            if refs:
                info["refs"] = refs

            self._defines[name] = info

    def _collect_elements(self, grammar_node: BagNode) -> None:
        """Extract elements from grammar and populate _schema.

        Args:
            grammar_node: The grammar root node.
        """
        if not grammar_node.is_branch:
            return

        # Recursively find all <element> tags
        self._extract_elements_recursive(grammar_node.value)

    def _extract_elements_recursive(self, bag: Bag) -> None:
        """Recursively extract elements from a Bag.

        Args:
            bag: Bag to search for elements.
        """
        for node in bag:
            base = self._get_base_tag(node.label)

            if base == "element":
                self._process_element(node)

            # Recurse into children
            if node.is_branch:
                self._extract_elements_recursive(node.value)

    def _process_element(self, elem_node: BagNode) -> None:
        """Process an <element> node and add to schema.

        Args:
            elem_node: The element BagNode.
        """
        tag = self._get_element_name(elem_node)
        if not tag or tag == "*" or ":" in tag:
            return

        # Skip if already in schema
        if self._schema.get_node(tag) is not None:
            return

        attrs: dict[str, Any] = {}

        # Check if element is void (has <empty/> or refs to empty define)
        if self._is_void_element(elem_node):
            attrs["sub_tags"] = ""

        # Collect refs for future content model resolution
        refs = self._collect_refs(elem_node)
        if refs:
            attrs["_refs"] = refs

        self._schema.set_item(tag, None, node_label=tag, **attrs)

    def _get_element_name(self, elem_node: BagNode) -> str | None:
        """Extract element name from <element> node.

        Name can be in:
        - <name> child element
        - 'name' attribute

        Args:
            elem_node: The element BagNode.

        Returns:
            Element name or None.
        """
        # Check 'name' attribute
        if "name" in elem_node.attr:
            return elem_node.attr["name"]

        # Check for <name> child
        if elem_node.is_branch:
            for child in elem_node.value:
                base = self._get_base_tag(child.label)
                if base == "name" and isinstance(child.value, str):
                    return child.value.strip()
        return None

    def _has_empty(self, node: BagNode) -> bool:
        """Check if node contains <empty/> tag.

        Args:
            node: BagNode to check.

        Returns:
            True if contains <empty/>.
        """
        if not node.is_branch:
            return False

        for child in node.value:
            base = self._get_base_tag(child.label)
            if base == "empty":
                return True
            if child.is_branch and self._has_empty(child):
                return True
        return False

    def _is_void_element(self, elem_node: BagNode) -> bool:
        """Check if element is void (no children allowed).

        An element is void if:
        - It directly contains <empty/>
        - It refs a define that contains <empty/>

        Args:
            elem_node: The element BagNode.

        Returns:
            True if void element.
        """
        # Direct <empty/>
        if self._has_empty(elem_node):
            return True

        # Check refs to .inner defines
        refs = self._collect_refs(elem_node)
        for ref in refs:
            if ref.endswith(".inner"):
                define_info = self._defines.get(ref, {})
                if define_info.get("empty"):
                    return True
        return False

    def _collect_refs(self, node: BagNode) -> list[str]:
        """Collect all <ref> names from a node.

        Args:
            node: BagNode to search.

        Returns:
            List of ref names.
        """
        refs: list[str] = []
        self._collect_refs_recursive(node, refs)
        return refs

    def _collect_refs_recursive(self, node: BagNode, refs: list[str]) -> None:
        """Recursively collect ref names.

        Args:
            node: BagNode to search.
            refs: List to append refs to.
        """
        base = self._get_base_tag(node.label)
        if base == "ref":
            name = node.attr.get("name", "")
            if name and name not in refs:
                refs.append(name)

        if node.is_branch:
            for child in node.value:
                self._collect_refs_recursive(child, refs)

    @property
    def elements(self) -> frozenset[str]:
        """Return all valid element names."""
        return frozenset(node.label for node in self._schema)

    def get_void_elements(self) -> frozenset[str]:
        """Return set of void element names."""
        void = set()
        for node in self._schema:
            if node.attr.get("sub_tags") == "":
                void.add(node.label)
        return frozenset(void)
