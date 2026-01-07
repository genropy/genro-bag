# Copyright 2025 Softwell S.r.l. - Genropy Team
# SPDX-License-Identifier: Apache-2.0

"""XsdBuilder - Dynamic builder generated from XSD schema.

Creates a builder class dynamically by parsing an XSD schema file.
The resulting builder populates the _schema dict used by BagBuilderBase
for validation.

The _schema format expected by BagBuilderBase is::

    _schema = {
        'element_name': {
            'children': set of allowed child tag names,
            'leaf': True if element cannot have children,
            'attrs': {
                'value': {  # validates the element's text content
                    'type': 'string|int|decimal|enum',
                    'pattern': 'regex pattern',
                    'values': ['allowed', 'enum', 'values'],
                    'minLength': int,
                    'maxLength': int,
                    'min': Decimal,  # minInclusive
                    'max': Decimal,  # maxInclusive
                }
            }
        }
    }

Example:
    >>> from genro_bag.builders import XsdBuilder
    >>>
    >>> builder = XsdBuilder('pain.001.001.12.xsd')
    >>>
    >>> from genro_bag import Bag
    >>> bag = Bag(builder=builder)
    >>> doc = bag.Document()
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from genro_bag.builders.base import BagBuilderBase

if TYPE_CHECKING:
    from genro_bag import Bag, BagNode


class XsdBuilder(BagBuilderBase):
    """Builder dynamically generated from XSD schema.

    Parses an XSD file and populates _schema for BagBuilderBase validation.
    """

    def __init__(self, xsd_source: str | Path):
        """Initialize builder from XSD file path or URL."""
        from genro_bag import Bag

        source = str(xsd_source)
        if source.startswith(("http://", "https://")):
            self._xsd_bag = Bag.from_url(source)
        else:
            xsd_content = Path(source).read_text()
            self._xsd_bag = Bag.from_xml(xsd_content)

        self._types: dict[str, dict] = {}
        self._schema: dict[str, dict] = {}
        self._build_schema()

    def _build_schema(self) -> None:
        """Convert XSD Bag to _schema dict."""
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
                self._types[name] = self._parse_complex_type(node)
            elif tag == "simpleType":
                self._types[name] = self._parse_simple_type(node)

        # Second pass: collect elements and resolve types
        for node in schema_node.value:
            tag = self._get_base_tag(node.label)
            name = node.attr.get("name")

            if tag == "element" and name:
                self._schema[name] = self._parse_element(node)

        # Resolve type references
        self._resolve_types()

    def _find_schema_node(self) -> BagNode | None:
        """Find the xs:schema root node."""
        for node in self._xsd_bag:
            base = self._get_base_tag(node.label)
            if base == "schema":
                return node
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

    def _parse_element(self, node: BagNode) -> dict:
        """Parse xs:element into schema spec."""
        spec: dict[str, Any] = {}
        type_ref = node.attr.get("type")

        if type_ref:
            spec["_type_ref"] = self._strip_ns(type_ref)

        # Check for inline complexType
        if node.is_branch:
            for child in node.value:
                child_tag = self._get_base_tag(child.label)
                if child_tag == "complexType":
                    inline = self._parse_complex_type(child)
                    spec.update(inline)
                    break

        return spec

    def _parse_complex_type(self, node: BagNode) -> dict:
        """Parse xs:complexType into schema spec."""
        spec: dict[str, Any] = {}
        children: set[str] = set()

        if node.is_branch:
            self._collect_children(node.value, children)

        if children:
            spec["children"] = children

        return spec

    def _collect_children(self, bag: Bag, children: set[str]) -> None:
        """Recursively collect child element names from compositors."""
        for node in bag:
            tag = self._get_base_tag(node.label)

            if tag == "element":
                name = node.attr.get("name") or node.attr.get("ref")
                if name:
                    name = self._strip_ns(name)
                    children.add(name)
                    # Register element if not in schema
                    if name not in self._schema:
                        self._schema[name] = self._parse_element(node)

            elif tag in ("sequence", "choice", "all", "complexType"):
                if node.is_branch:
                    self._collect_children(node.value, children)

    def _parse_simple_type(self, node: BagNode) -> dict:
        """Parse xs:simpleType into schema spec with validation attrs."""
        spec: dict[str, Any] = {"leaf": True}
        attrs: dict[str, Any] = {}

        if not node.is_branch:
            return spec

        for child in node.value:
            child_tag = self._get_base_tag(child.label)

            if child_tag == "restriction":
                base = child.attr.get("base", "")
                base_type = self._strip_ns(base)
                attrs["type"] = self._xsd_type_to_attr_type(base_type)

                if child.is_branch:
                    self._parse_restrictions(child.value, attrs)

        if attrs:
            spec["attrs"] = {"value": attrs}

        return spec

    def _parse_restrictions(self, bag: Bag, attrs: dict) -> None:
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
        for _elem_name, spec in self._schema.items():
            type_ref = spec.pop("_type_ref", None)
            if not type_ref:
                continue

            # Built-in XSD types
            if type_ref in ("string", "integer", "decimal", "date", "dateTime", "boolean"):
                spec["leaf"] = True
                spec["attrs"] = {"value": {"type": self._xsd_type_to_attr_type(type_ref)}}
                continue

            # Reference to defined type
            if type_ref in self._types:
                type_spec = self._types[type_ref]
                for key, value in type_spec.items():
                    if key not in spec:
                        spec[key] = value

    @property
    def elements(self) -> frozenset[str]:
        """Return all valid element names."""
        return frozenset(self._schema.keys())

    def get_children(self, element: str) -> frozenset[str] | None:
        """Get allowed children for an element."""
        spec = self._schema.get(element, {})
        children = spec.get("children")
        return frozenset(children) if children else None
