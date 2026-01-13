# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""XsdBuilder - Dynamic builder generated from XSD schema.

Creates a builder class dynamically by parsing an XSD schema file at runtime.
The resulting builder populates _schema (a Bag) used by BagBuilderBase.

This is different from XsdSchemaBuilder which pre-compiles schemas to files.
XsdBuilder parses XSD at runtime for immediate use.

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.builders import XsdBuilder
    >>>
    >>> bag = Bag(builder=XsdBuilder, builder_xsd_source='pain.001.001.12.xsd')
    >>> doc = bag.Document()
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from genro_bag.builder import BagBuilderBase

if TYPE_CHECKING:
    from genro_bag import Bag, BagNode


class XsdBuilder(BagBuilderBase):
    """Builder dynamically generated from XSD schema.

    Parses an XSD file at runtime and populates _schema for BagBuilderBase validation.
    For pre-compiled schemas, use XsdSchemaBuilder instead.
    """

    def __init__(self, bag: Bag, xsd_source: str | Path):
        """Initialize builder from XSD file path or URL.

        Args:
            bag: The Bag instance this builder is attached to.
            xsd_source: Path to XSD file or URL to fetch XSD from.
        """
        from genro_bag import Bag as BagClass

        super().__init__(bag)

        source = str(xsd_source)
        if source.startswith(("http://", "https://")):
            self._xsd_bag = BagClass.from_url(source)
        else:
            xsd_content = Path(source).read_text()
            self._xsd_bag = BagClass.from_xml(xsd_content)

        self._types: Bag = BagClass()
        self._schema: Bag = BagClass()
        self._build_schema()

    def _build_schema(self) -> None:
        """Convert XSD Bag to _schema Bag."""
        schema_node = self._find_schema_node()
        if schema_node is None:
            return

        # First pass: collect all type definitions
        for node in schema_node.value:
            tag = self._get_base_tag(node.label)
            name = node.attr.get("name")

            if not name:
                continue

            if tag == "complexType":
                children_bag, attrs = self._parse_complex_type(node)
                self._types.set_item(name, children_bag, **attrs)
            elif tag == "simpleType":
                attrs = self._parse_simple_type(node)
                self._types.set_item(name, None, **attrs)

        # Second pass: collect elements and resolve types
        for node in schema_node.value:
            tag = self._get_base_tag(node.label)
            name = node.attr.get("name")

            if tag == "element" and name:
                children_bag, attrs = self._parse_element(node)
                self._schema.set_item(name, children_bag, **attrs)

        # Resolve type references
        self._resolve_types()

    def _find_schema_node(self) -> BagNode | None:
        """Find the xs:schema root node."""
        for node in self._xsd_bag:
            base = self._get_base_tag(node.label)
            if base == "schema":
                return node  # type: ignore[no-any-return]
        return None

    def _get_base_tag(self, label: str) -> str:
        """Extract base tag: 'xs:simpleType_1' -> 'simpleType'."""
        # Remove namespace prefix
        if ":" in label:
            label = label.split(":")[-1]
        # Remove numeric suffix
        if "_" in label:
            label = label.rsplit("_", 1)[0]
        return label

    def _parse_element(self, node: BagNode) -> tuple[Bag | None, dict[str, Any]]:
        """Parse xs:element into (children_bag, attrs)."""
        attrs: dict[str, Any] = {}
        children_bag: Bag | None = None
        type_ref = node.attr.get("type")

        if type_ref:
            attrs["_type_ref"] = self._strip_ns(type_ref)

        # Check for inline complexType
        if node.is_branch:
            for child in node.value:
                child_tag = self._get_base_tag(child.label)
                if child_tag == "complexType":
                    children_bag, inline_attrs = self._parse_complex_type(child)
                    attrs.update(inline_attrs)
                    break

        return children_bag, attrs

    def _parse_complex_type(self, node: BagNode) -> tuple[Bag | None, dict[str, Any]]:
        """Parse xs:complexType into (children_bag, attrs)."""
        from genro_bag import Bag as BagClass

        attrs: dict[str, Any] = {}
        children_bag: Bag | None = None

        if node.is_branch:
            children_bag = BagClass()
            self._collect_children(node.value, children_bag)
            if len(children_bag) == 0:
                children_bag = None

        return children_bag, attrs

    def _collect_children(self, source_bag: Bag, children_bag: Bag) -> None:
        """Recursively collect child element names from compositors (ordered)."""
        for node in source_bag:
            tag = self._get_base_tag(node.label)

            if tag == "element":
                name = node.attr.get("name") or node.attr.get("ref")
                if name:
                    name = self._strip_ns(name)
                    # Add to children_bag only if not already present
                    if children_bag.node(name) is None:
                        children_bag.set_item(name, None)
                    # Register element in _schema if not present
                    if self._schema.node(name) is None:
                        elem_children, elem_attrs = self._parse_element(node)
                        self._schema.set_item(name, elem_children, **elem_attrs)

            elif tag in ("sequence", "choice", "all", "complexType"):
                if node.is_branch:
                    self._collect_children(node.value, children_bag)

    def _parse_simple_type(self, node: BagNode) -> dict[str, Any]:
        """Parse xs:simpleType into node attrs dict."""
        result: dict[str, Any] = {"leaf": True}
        value_attrs: dict[str, Any] = {}

        if not node.is_branch:
            return result

        for child in node.value:
            child_tag = self._get_base_tag(child.label)

            if child_tag == "restriction":
                base = child.attr.get("base", "")
                base_type = self._strip_ns(base)
                value_attrs["type"] = self._xsd_type_to_attr_type(base_type)

                if child.is_branch:
                    self._parse_restrictions(child.value, value_attrs)

        if value_attrs:
            result["attrs"] = {"value": value_attrs}

        return result

    def _parse_restrictions(self, bag: Bag, attrs: dict[str, Any]) -> None:
        """Parse restriction facets into attrs dict."""
        for node in bag:
            tag = self._get_base_tag(node.label)
            value = node.attr.get("value")

            if tag == "pattern":
                attrs["pattern"] = value
            elif tag == "enumeration":
                if "values" not in attrs:
                    attrs["values"] = []
                    attrs["type"] = "enum"
                attrs["values"].append(value)
            elif tag == "minLength":
                attrs["minLength"] = int(value)
            elif tag == "maxLength":
                attrs["maxLength"] = int(value)
            elif tag == "minInclusive":
                attrs["min"] = Decimal(value)
            elif tag == "maxInclusive":
                attrs["max"] = Decimal(value)
            elif tag == "totalDigits":
                attrs["totalDigits"] = int(value)
            elif tag == "fractionDigits":
                attrs["fractionDigits"] = int(value)

    def _xsd_type_to_attr_type(self, xsd_type: str) -> str:
        """Convert XSD base type to attrs type."""
        mapping = {
            "string": "string",
            "integer": "int",
            "int": "int",
            "decimal": "decimal",
            "boolean": "bool",
            "date": "string",
            "dateTime": "string",
        }
        return mapping.get(xsd_type, "string")

    def _strip_ns(self, name: str) -> str:
        """Strip namespace prefix: 'xs:string' -> 'string'."""
        return name.split(":")[-1] if ":" in name else name

    def _resolve_types(self) -> None:
        """Resolve type references in schema elements."""
        for schema_node in self._schema:
            type_ref = schema_node.attr.pop("_type_ref", None)
            if not type_ref:
                continue

            # Built-in XSD types
            if type_ref in ("string", "integer", "decimal", "date", "dateTime", "boolean"):
                schema_node.attr["leaf"] = True
                schema_node.attr["attrs"] = {
                    "value": {"type": self._xsd_type_to_attr_type(type_ref)}
                }
                continue

            # Reference to defined type
            type_node = self._types.node(type_ref)
            if type_node is not None:
                # Copy children from type if element has none
                if schema_node.get_value(static=True) is None:
                    type_children = type_node.get_value(static=True)
                    if type_children is not None:
                        schema_node.set_value(type_children)
                # Copy attrs from type if not present
                for key, value in type_node.attr.items():
                    if key not in schema_node.attr:
                        schema_node.attr[key] = value

    @property
    def elements(self) -> frozenset[str]:
        """Return all valid element names."""
        return frozenset(node.label for node in self._schema)

    def get_children(self, element: str) -> frozenset[str] | None:
        """Get allowed children for an element (ordered)."""
        schema_node = self._schema.node(element)
        if schema_node is None:
            return None
        children_bag = schema_node.get_value(static=True)
        if children_bag is None:
            return None
        return frozenset(node.label for node in children_bag)
